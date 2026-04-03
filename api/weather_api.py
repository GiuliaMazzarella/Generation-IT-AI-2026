# api/weather_api.py

"""
Chiamate HTTP verso Open-Meteo per recuperare il meteo attuale.

Questo modulo fornisce la funzione `get_weather(latitude, longitude)` che
interroga l'endpoint configurato in `config.BASE_URL` e restituisce il JSON
ritornato dalla API.

Esempio:
    >>> from api.weather_api import get_weather
    >>> get_weather(45.4642, 9.1900)
    {'current_weather': {'temperature': 12, ...}}
"""

import logging
from typing import Dict, Any
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import BASE_URL, DEFAULT_PARAMS, CACHE_TTL, CACHE_STALE_TTL, CACHE_PRECISION, BACKGROUND_REFRESH_ENABLED, PERSISTENT_CACHE_ENABLED
from exceptions import WeatherAPIError, InvalidCoordinatesError
from metrics import inc_counter
from cache import SimpleCache
# Removed unused Optional import

logger = logging.getLogger(__name__)

# Cache persistente opzionale per risposte meteo (disabilitata di default per minimizzare i dati utente su disco)
_cache_file = '.weather_cache.pkl' if PERSISTENT_CACHE_ENABLED else None
_cache_api = SimpleCache(_cache_file)

# In-flight deduplication: key -> (Event, result_container)
from threading import Event, Lock as ThreadLock
_inflight: Dict[str, Any] = {}
_inflight_lock = ThreadLock()

# small thread pool for background revalidation
_executor = ThreadPoolExecutor(max_workers=2)


def _get_or_wait_inflight(key: str, fetch_callable):
    """If another thread is fetching the same key, wait and return its result.
    Otherwise, register as in-flight and perform fetch_callable().
    """
    with _inflight_lock:
        if key in _inflight:
            event, container = _inflight[key]
            # release lock and wait
            # waiting thread will read container[0]
            need_wait = True
        else:
            event = Event()
            container = [None, None]  # [result, exception]
            _inflight[key] = (event, container)
            need_wait = False

    if need_wait:
        event.wait()
        # after event is set, return or raise
        result, exc = container[0], container[1]
        if exc:
            raise exc
        return result

    # we are the leader for this key
    try:
        result = fetch_callable()
        container[0] = result
        return result
    except Exception as e:
        container[1] = e
        raise
    finally:
        # signal waiting threads and remove inflight
        event.set()
        with _inflight_lock:
            try:
                del _inflight[key]
            except KeyError:
                pass


def _get_session_with_retries() -> requests.Session:
    """
    Crea e ritorna una `requests.Session` configurata con retry/backoff.

    Nota eco-friendly: riduce il numero di retry a 1 per limitare le chiamate
    ripetute in caso di errori transitori (tradeoff resilienza/consumo).
    """
    session = requests.Session()
    # Ridotto total retries per comportamento eco-friendly
    retry = Retry(total=1, backoff_factor=0.2, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _validate_coords(latitude, longitude):
    """
    Validazione semplice per latitudine e longitudine.

    Args:
        latitude: valore numerico o stringa convertibile in float.
        longitude: valore numerico o stringa convertibile in float.

    Raises:
        InvalidCoordinatesError: se i valori non sono numerici o fuori range.
    """
    try:
        lat = float(latitude)
        lon = float(longitude)
    except Exception:
        raise InvalidCoordinatesError("Latitude and longitude must be numeric")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise InvalidCoordinatesError("Latitude or longitude out of range")


def _get_weather_uncached(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Funzione che esegue realmente la chiamata HTTP a Open-Meteo per fornire
    i dati meteo per coordinate specifiche (non cached).
    """
    # Incrementa contatore di chiamate uncached
    try:
        inc_counter('weather_api.uncached_requests')
    except Exception:
        pass

    try:
        params = DEFAULT_PARAMS.copy()
        params["latitude"] = float(latitude)
        params["longitude"] = float(longitude)
        # Primary cached request: request times in UTC so cache is consistent
        params['timezone'] = 'UTC'

        session = _get_session_with_retries()
        response = session.get(BASE_URL, params=params, timeout=10)

        if response.status_code != 200:
            logger.error("Errore API: %s", response.status_code)
            raise WeatherAPIError(f"API returned status {response.status_code}")

        try:
            return response.json()
        except ValueError as e:
            logger.exception("Errore nel parsing della risposta JSON: %s", e)
            raise WeatherAPIError("Invalid JSON response")
    except requests.exceptions.RequestException as e:
        logger.exception("Errore nella richiesta API: %s", e)
        raise WeatherAPIError(str(e))


@lru_cache(maxsize=256)
def _get_weather_cached(lat_rounded: float, lon_rounded: float) -> Dict[str, Any]:
    """
    Wrapper cached: chiama `_get_weather_uncached` con coordinate arrotondate.
    Usare arrotondamento limita chiamate ridondanti per coordinate molto simili.
    """
    return _get_weather_uncached(lat_rounded, lon_rounded)


def _round_coords(latitude: float, longitude: float, precision: int = 3):
    """Arrotonda le coordinate a `precision` decimali per la cache key."""
    return (round(float(latitude), precision), round(float(longitude), precision))


def get_weather(latitude, longitude, ttl: int = None, stale_ttl: int = None) -> Dict[str, Any]:
    """
    Recupera i dati meteo da Open-Meteo.

    Usa una cache LRU per evitare chiamate ripetute a parità di coordinate
    (arrotondate) e una cache persistente per fallback offline.

    Args:
        latitude: latitudine della posizione (float o stringa convertibile).
        longitude: longitudine della posizione (float o stringa convertibile).
        ttl: tempo in secondi per considerare la cache persistente fresca.
        stale_ttl: tempo in secondi per considerare i dati "stale but usable" in assenza di rete.

    Returns:
        Il payload JSON restituito dall'API (come dict) con chiave speciale `_meta` che contiene `source` e `age_seconds`.

    Raises:
        InvalidCoordinatesError: se lat/lon non sono validi.
        WeatherAPIError: per errori HTTP, network o parsing JSON (solo se nessun fallback disponibile).
    """
    # Use defaults from config if None
    if ttl is None:
        ttl = CACHE_TTL
    if stale_ttl is None:
        stale_ttl = CACHE_STALE_TTL

    # Validazione input
    _validate_coords(latitude, longitude)

    # Incrementa contatore totale richieste (inclusi cache hits)
    try:
        inc_counter('weather_api.total_requests')
    except Exception:
        pass

    lat_r, lon_r = _round_coords(latitude, longitude, precision=CACHE_PRECISION)
    key = f"weather:{lat_r}:{lon_r}"

    # Try to fetch fresh and persist to disk; on failure, return stale if available
    def fetch():
        # call cached function as before (it has its own in-memory LRU)
        return _get_weather_cached(lat_r, lon_r)

    # Use deduplication to avoid parallel identical fetches
    result = _get_or_wait_inflight(key, lambda: _cache_api.get_or_fetch(key, fetch, ttl=ttl, stale_ttl=stale_ttl))

    # attach metadata: age and source
    try:
        cached_info = _cache_api.get_with_age(key)
        if cached_info is not None:
            cached_value, age = cached_info
            source = 'live' if age <= ttl else 'stale'
        else:
            age = 0
            source = 'live'
    except Exception:
        age = 0
        source = 'live'

    # If returned stale and background refresh enabled, schedule refresh (do not block)
    try:
        if source == 'stale' and BACKGROUND_REFRESH_ENABLED:
            def _bg_refresh():
                try:
                    # fetch fresh and update cache
                    _cache_api.get_or_fetch(key, fetch, ttl=ttl, stale_ttl=stale_ttl)
                except Exception:
                    # ignore background errors
                    pass
            _executor.submit(_bg_refresh)
    except Exception:
        pass

    # Ensure result contains current_weather; attach _meta
    if isinstance(result, dict):
        out = dict(result)
    else:
        out = { 'current_weather': result }
    out['_meta'] = {'source': source, 'age_seconds': age}
    # Ensure cw is always defined (avoids warnings when referenced later)
    cw = out.get('current_weather')

    # Compute and attach place-local UTC time representation for current_weather if possible.
    try:
        if isinstance(cw, dict):
            time_str = cw.get('time')
            tz_name = out.get('timezone')
            if time_str:
                from datetime import datetime, timezone
                try:
                    # Parse the local time (likely naive or with offset); prefer zoneinfo tz_name
                    dt = datetime.fromisoformat(time_str)
                except Exception:
                    dt = None

                if dt is not None:
                    try:
                        # If tz_name is provided (IANA), attach it and convert to UTC
                        if isinstance(tz_name, str) and '/' in tz_name:
                            from zoneinfo import ZoneInfo
                            dt_local = dt.replace(tzinfo=ZoneInfo(tz_name)) if dt.tzinfo is None else dt
                            dt_utc = dt_local.astimezone(timezone.utc)
                        else:
                            # If dt has offset info, convert to UTC directly; otherwise assume it's local with unknown tz => treat as UTC fallback
                            if dt.tzinfo is not None:
                                dt_utc = dt.astimezone(timezone.utc)
                            else:
                                # fallback: treat as UTC
                                dt_utc = dt.replace(tzinfo=timezone.utc)
                        # attach UTC representations
                        try:
                            cw['time_utc'] = dt_utc.isoformat()
                            cw['time_utc_formatted'] = dt_utc.strftime('%d %b %Y, %H:%M UTC')
                        except Exception:
                            cw['time_utc'] = dt_utc.isoformat()
                            cw['time_utc_formatted'] = dt_utc.strftime('%d %b %Y, %H:%M')
                    except Exception:
                        # non-critical
                        pass
                # Now attempt a lightweight call to get place-local time (timezone=auto)
                try:
                    session = _get_session_with_retries()
                    local_params = {'latitude': float(latitude), 'longitude': float(longitude), 'current_weather': True, 'timezone': 'auto'}
                    r2 = session.get(BASE_URL, params=local_params, timeout=6)
                    if r2.status_code == 200:
                        j2 = r2.json()
                        lcw = j2.get('current_weather') or {}
                        ltz = j2.get('timezone')
                        # attach local time fields
                        if lcw.get('time'):
                            try:
                                from datetime import datetime
                                raw_local = lcw.get('time')
                                # Try to parse the returned local time and format it human-friendly
                                try:
                                    dt_local = datetime.fromisoformat(raw_local)
                                    # if timezone known (ltz) and dt_local naive, attach it to produce nicer output
                                    if isinstance(ltz, str) and '/' in ltz:
                                        try:
                                            from zoneinfo import ZoneInfo
                                            if dt_local.tzinfo is None:
                                                dt_local = dt_local.replace(tzinfo=ZoneInfo(ltz))
                                        except Exception:
                                            pass
                                    # attach iso and formatted
                                    try:
                                        cw['time_local'] = dt_local.isoformat()
                                    except Exception:
                                        cw['time_local'] = raw_local
                                    try:
                                        # prefer including timezone name when available
                                        cw['time_local_formatted'] = dt_local.strftime('%d %b %Y, %H:%M %Z')
                                    except Exception:
                                        try:
                                            cw['time_local_formatted'] = dt_local.strftime('%d %b %Y, %H:%M')
                                        except Exception:
                                            cw['time_local_formatted'] = raw_local
                                except Exception:
                                    # parsing failed: fall back to raw string
                                    cw['time_local'] = raw_local
                                    cw['time_local_formatted'] = raw_local
                            except Exception:
                                pass
                except Exception:
                    # ignore local time errors
                    pass
    except Exception:
        # Non-critical: ignore if we can't produce local time
        pass

    # If coastal, fetch basic sea/wave info (lightweight hourly request)
    try:
        # lazy import to avoid circular deps
        from utils.geocoder import is_coastal
        coastal = False
        try:
            coastal = is_coastal(latitude, longitude)
        except Exception:
            coastal = False

        if coastal:
            # ensure cw is a dict for safe indexing
            cw_local = out.get('current_weather') or {}
            try:
                session = _get_session_with_retries()
                params = DEFAULT_PARAMS.copy()
                params['latitude'] = float(latitude)
                params['longitude'] = float(longitude)
                # request wave-related hourly fields
                params['hourly'] = 'wave_height,wave_period,wave_direction'
                resp = session.get(BASE_URL, params=params, timeout=8)
                if resp.status_code == 200:
                    j = resp.json()
                    hourly = j.get('hourly') or {}
                    times = hourly.get('time') or []
                    # pick index matching current_weather.time if possible
                    idx = None
                    if cw_local.get('time') and times:
                        try:
                            idx = times.index(cw_local.get('time'))
                        except ValueError:
                            idx = None
                    # fallback to nearest (last)
                    if idx is None and times:
                        idx = len(times) - 1

                    if idx is not None and idx >= 0:
                        sea = {}
                        wh = hourly.get('wave_height')
                        wp = hourly.get('wave_period')
                        wd = hourly.get('wave_direction')
                        try:
                            if wh and len(wh) > idx:
                                sea['wave_height'] = wh[idx]
                            if wp and len(wp) > idx:
                                sea['wave_period'] = wp[idx]
                            if wd and len(wd) > idx:
                                sea['wave_direction'] = wd[idx]
                        except Exception:
                            pass
                        if sea:
                            out['sea'] = sea
            except Exception:
                # non-critical: ignore sea fetch failures
                pass
    except Exception:
        pass
    return out

# Utility functions for cache management

def cache_clear(area: str = 'all') -> None:
    """Clears caches; area can be 'all', 'weather'."""
    if area in ('all', 'weather'):
        try:
            _cache_api.clear()
        except Exception:
            pass


def cache_status() -> Dict[str, Any]:
    """Returns simple status of weather cache (keys count)."""
    try:
        keys = _cache_api.keys()
        return {'weather_cache_keys': len(keys)}
    except Exception:
        return {'weather_cache_keys': None}


def get_forecast(latitude, longitude, days: int = 5) -> Dict[str, Any]:
    """Fetch basic daily forecast for the next `days` days from Open-Meteo.

    Returns the parsed JSON from the API (dict). Raises WeatherAPIError on network errors.
    """
    _validate_coords(latitude, longitude)
    try:
        params = {
            'latitude': float(latitude),
            'longitude': float(longitude),
            'daily': 'temperature_2m_max,temperature_2m_min,weathercode',
            'timezone': 'auto'
        }
        session = _get_session_with_retries()
        resp = session.get(BASE_URL, params=params, timeout=12)
        if resp.status_code != 200:
            logger.error("Forecast API returned status %s", resp.status_code)
            raise WeatherAPIError(f"Forecast API returned status {resp.status_code}")
        try:
            return resp.json()
        except ValueError:
            raise WeatherAPIError("Invalid JSON in forecast response")
    except requests.exceptions.RequestException as e:
        logger.exception("Network error fetching forecast: %s", e)
        raise WeatherAPIError(str(e))
