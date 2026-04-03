# utils/geocoder.py
"""
Geocoding utilities for the Weather App.

Questo modulo fornisce funzioni per convertire un nome di città in coordinate
(latitudine, longitudine) usando Nominatim (geopy). La funzione pubblica
`get_coordinates` normalizza l'input e utilizza una cache LRU per ridurre le
chiamate ripetute.

Esempio:
    >>> from utils.geocoder import get_coordinates
    >>> get_coordinates('Milano')
    {'latitude': 45.4642, 'longitude': 9.1900}
"""

import re
from functools import lru_cache
from typing import Optional, Dict, Any
import logging

from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

from exceptions import GeocodingError, GeocodingNotFoundError
from metrics import inc_counter
from cache import SimpleCache
from config import CACHE_TTL, NEGATIVE_CACHE_TTL, PERSISTENT_CACHE_ENABLED

logger = logging.getLogger(__name__)

# Cache persistente opzionale per geocodifica (disabilitata di default per ridurre la conservazione dei dati utente)
_geocode_cache = SimpleCache('.geocode_cache.pkl' if PERSISTENT_CACHE_ENABLED else None)


def _get_rate_limited_geocoder():
    """Create the rate-limited geocoder lazily so tests can monkeypatch `Nominatim`."""
    geolocator = Nominatim(user_agent="weather_app")
    return RateLimiter(
        geolocator.geocode,
        min_delay_seconds=1.1,
        max_retries=1,
        error_wait_seconds=2.0,
        swallow_exceptions=False,
    )

# In-flight deduplication for geocoding
from threading import Event, Lock as ThreadLock
_inflight_geo: Dict[str, Any] = {}
_inflight_geo_lock = ThreadLock()


def _is_city_like_location(raw: Dict[str, Any]) -> bool:
    """Return True only if a Nominatim result is a proper populated place.

    Two-tier strategy:
    1. High-importance bypass (>= 0.5): well-known world cities are accepted
       regardless of addresstype (e.g. Tokyo → "province", which would otherwise
       be filtered out).
    2. Low-importance: require a strict allow-list of populated-place addresstypes
       and a minimum importance of 0.1 to filter out obscure POIs (cafes, roads…).
    """
    if not isinstance(raw, dict):
        return False

    try:
        importance = float(raw.get('importance') or 0.0)
    except (TypeError, ValueError):
        importance = 0.0

    # Tier 1: well-known city → accept directly
    if importance >= 0.5:
        return True

    # Tier 2: lower-profile place → require city-like addresstype
    addresstype = str(raw.get('addresstype') or '').lower()
    allowed_addresstypes = {
        'city', 'town', 'village', 'municipality',
        'hamlet', 'locality', 'suburb', 'quarter',
    }
    return addresstype in allowed_addresstypes and importance >= 0.3


def _get_or_wait_inflight_geo(key: str, fetch_callable):
    with _inflight_geo_lock:
        if key in _inflight_geo:
            event, container = _inflight_geo[key]
            need_wait = True
        else:
            event = Event()
            container = [None, None]
            _inflight_geo[key] = (event, container)
            need_wait = False

    if need_wait:
        event.wait()
        result, exc = container[0], container[1]
        if exc:
            raise exc
        return result

    try:
        result = fetch_callable()
        container[0] = result
        return result
    except Exception as e:
        container[1] = e
        raise
    finally:
        event.set()
        with _inflight_geo_lock:
            try:
                del _inflight_geo[key]
            except KeyError:
                pass


@lru_cache(maxsize=256)
def _geocode_cached(normalized_city: str) -> Optional[Dict[str, float]]:
    """
    Effettua la chiamata reale a Nominatim per una città già normalizzata.

    Args:
        normalized_city: Nome della città normalizzato (es. strip, lower se necessario).

    Returns:
        Dizionario con chiavi `latitude` e `longitude` se la geocodifica ha
        successo.

    Raises:
        GeocodingNotFoundError: se Nominatim non trova corrispondenze per la città.
        GeocodingError: per errori di rete o altri problemi interni.

    Nota:
        Funzione interna con cache LRU. Non normalizza il nome della città;
        questo compito è lasciato alla funzione pubblica `get_coordinates`.
    """
    # incrementa contatore di chiamate uncached al geocoder
    try:
        inc_counter('geocoder.uncached_requests')
    except Exception:
        pass

    try:
        location = _get_rate_limited_geocoder()(normalized_city, timeout=10)

        if location is None:
            raise GeocodingNotFoundError(f"City not found: {normalized_city}")

        raw = getattr(location, 'raw', None) or {}
        if raw:
            if not _is_city_like_location(raw):
                raise GeocodingNotFoundError(f"City not found: {normalized_city}")

            # Name-match check: the user's query must appear as a whole word in the
            # ASCII/Latin portion of the returned place name. This blocks partial-
            # substring hits like "casa" → Casablanca and transliteration hits like
            # "dado" → Korean 다도면.
            # Cities with a purely non-Latin name (e.g. Tokyo → 東京都) have no
            # ASCII portion, so the check is skipped and importance alone decides.
            name = str(raw.get('name') or '')
            display = str(raw.get('display_name') or '')
            # Strip non-ASCII chars to get the Latin-script portion of the name.
            name_latin = re.sub(r'[^\x00-\x7F]+', ' ', name).strip()
            if name_latin:
                query_lower = normalized_city.lower()
                pattern = r'\b' + re.escape(query_lower) + r'\b'
                display_latin = re.sub(r'[^\x00-\x7F]+', ' ', display).strip()
                if not re.search(pattern, name_latin.lower()) and \
                   not re.search(pattern, display_latin.lower()):
                    raise GeocodingNotFoundError(f"City not found: {normalized_city}")

        return {"latitude": location.latitude, "longitude": location.longitude}

    except GeocodingNotFoundError:
        # rialza la specifica eccezione
        raise
    except Exception as e:
        logger.exception("Errore durante la geocodifica: %s", e)
        raise GeocodingError(str(e))


def get_coordinates(city_name: str, ttl: int = 86400, stale_ttl: int = 7 * 86400) -> Dict[str, float]:
    """
    Converte il nome di una città in coordinate geografiche (latitudine, longitudine).

    Args:
        city_name: Nome della città fornito dall'utente (es. "Milano"). Deve essere
            una stringa non vuota.
        ttl: tempo in secondi per considerare la cache persistente fresca.
        stale_ttl: tempo in secondi per considerare i dati "stale but usable".

    Returns:
        Un dizionario con le chiavi `latitude` e `longitude` (float).

    Raises:
        GeocodingError: se l'input non è valido o si verifica un errore durante la
            geocodifica.
        GeocodingNotFoundError: se la città non viene trovata.

    Example:
        >>> get_coordinates('Roma')
        {'latitude': 41.8933, 'longitude': 12.4829}
    """
    if not isinstance(city_name, str) or not city_name.strip():
        raise GeocodingError("Invalid city name")

    # incrementa contatore totale richieste al geocoder (anche cache hits)
    try:
        inc_counter('geocoder.total_requests')
    except Exception:
        pass

    normalized = city_name.strip()
    # Normalize cache key to avoid duplicate misses for case variants
    # such as "Milano" vs "milano".
    cache_token = normalized.casefold()
    key = f"geocode:{cache_token}"

    # 1) Controlla se c'è un risultato fresco nella cache persistente
    try:
        cached = _geocode_cache.get(key, max_age=ttl)
        if cached is not None:
            # gestione risultato negativo memorizzato
            if isinstance(cached, dict) and cached.get('__not_found__'):
                raise GeocodingNotFoundError(f"City not found (cached): {normalized}")
            return cached
    except Exception:
        # ignoriamo errori di cache e procediamo con fetch
        cached = None

    # 2) Definisci la fetch che userà anche la LRU in-memory
    def fetch():
        return _geocode_cached(cache_token)

    # 3) Prova a fetchare; se fallisce con GeocodingNotFoundError, memorizza risultato negativo
    try:
        result = _get_or_wait_inflight_geo(key, lambda: _geocode_cache.get_or_fetch(key, fetch, ttl=ttl, stale_ttl=stale_ttl))
        # If a negative marker is returned from cache/get_or_fetch, convert it
        # into the expected domain exception instead of leaking invalid shape.
        if isinstance(result, dict) and result.get('__not_found__'):
            raise GeocodingNotFoundError(f"City not found (cached): {normalized}")
        return result
    except GeocodingNotFoundError:
        # memorizza un marker negativo per evitare ripetute chiamate per la stessa città
        try:
            _geocode_cache.set(key, {'__not_found__': True})
        except Exception:
            pass
        raise
    except Exception:
        # altre eccezioni (network) -> rialza come GeocodingError
        raise


@lru_cache(maxsize=1024)
def is_coastal(latitude: float, longitude: float) -> bool:
    """Heuristic: use Nominatim reverse geocoding to see if the location is on/near the coast.

    Returns True if reverse geocoder indicates the place is a coastline/sea or contains keywords.
    This is a heuristic and may not be 100% accurate, but is sufficient to decide whether to fetch sea data.
    """
    try:
        geolocator = Nominatim(user_agent="weather_app")
        # zoom 8-10 gives area-level info; we use 8 to get broader context
        loc = geolocator.reverse((float(latitude), float(longitude)), exactly_one=True, timeout=10)
        if not loc:
            return False
        raw = loc.raw or {}
        # Check type/class
        typ = raw.get('type', '') or ''
        cls = raw.get('class', '') or ''
        display = raw.get('display_name', '') or ''
        address = raw.get('address', {}) or {}

        keywords = ['sea', 'ocean', 'coast', 'bay', 'gulf', 'mare', 'marina']
        # If type or class suggests coastline or water
        if typ and any(k in typ.lower() for k in keywords):
            return True
        if cls and any(k in cls.lower() for k in keywords):
            return True
        # address keys like 'water' or 'coastline'
        for v in address.values():
            if isinstance(v, str) and any(k in v.lower() for k in keywords):
                return True
        # fallback: check display name
        if any(k in display.lower() for k in keywords):
            return True
    except Exception:
        # any error => consider not coastal to avoid extra API calls
        return False
    return False
