from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from utils.geocoder import get_coordinates
from api.weather_api import get_weather
from exceptions import GeocodingNotFoundError, GeocodingError, WeatherAPIError
from config import ADMIN_TOKEN
from api import weather_api
from utils import geocoder
import os

app = FastAPI(title="Weather App UI")

# mount static and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def _is_admin_authorized(request: Request) -> bool:
    """Return True if request is authorized to perform admin actions.

    Permissive rules (intended for local development):
    - If env var WEATHER_ALLOW_WEAK_ADMIN is set to '1', allow.
    - If the client IP is localhost (127.0.0.1, ::1), allow.
    - Otherwise require exact match of header 'x-admin-token' to ADMIN_TOKEN.

    This relaxes protection for dev use; keep it explicit so it can be reverted.
    """
    # Env override for quick developer convenience
    if os.getenv('WEATHER_ALLOW_WEAK_ADMIN') == '1':
        return True

    if not request:
        return False

    try:
        client_host = request.client.host if request.client else None
    except Exception:
        client_host = None

    if client_host in ('127.0.0.1', '::1', 'localhost'):
        return True

    token = request.headers.get('x-admin-token') if request else None
    return token == ADMIN_TOKEN


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Ritorna pagina HTML principale con form di ricerca."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/weather")
async def api_weather(city: str = None):
    """Endpoint JSON per ottenere il meteo per una città."""
    if not city or not city.strip():
        raise HTTPException(status_code=400, detail="city parameter is required")

    try:
        coords = get_coordinates(city)
    except GeocodingNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except GeocodingError as e:
        raise HTTPException(status_code=503, detail=str(e))

    try:
        data = get_weather(coords["latitude"], coords["longitude"])
        return JSONResponse({"status": "ok", "data": data})
    except WeatherAPIError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/weather/multi')
async def api_weather_multi(cities: str = None):
    """Return weather for multiple cities provided as a comma-separated list in `cities`.

    Response shape: { status: 'ok', results: [ { city, status: 'ok'|'error', data?, error? }, ... ] }
    """
    if not cities or not cities.strip():
        raise HTTPException(status_code=400, detail='cities parameter is required (comma-separated)')

    names = [c.strip() for c in cities.split(',') if c.strip()]
    results = []
    for name in names:
        try:
            coords = get_coordinates(name)
        except GeocodingNotFoundError as e:
            results.append({"city": name, "status": "error", "error": str(e)})
            continue
        except GeocodingError as e:
            results.append({"city": name, "status": "error", "error": str(e)})
            continue

        try:
            data = get_weather(coords["latitude"], coords["longitude"])
            results.append({"city": name, "status": "ok", "data": data})
        except WeatherAPIError as e:
            results.append({"city": name, "status": "error", "error": str(e)})
        except Exception as e:
            results.append({"city": name, "status": "error", "error": str(e)})

    return JSONResponse({"status": "ok", "results": results})


@app.post("/api/cache/clear")
async def api_cache_clear(area: str = 'all', request: Request = None):
    """Clear cache endpoint, protected by admin token in header 'x-admin-token'."""
    # Use permissive helper: allows localhost or env override for dev
    if not _is_admin_authorized(request):
        raise HTTPException(status_code=403, detail="Forbidden")

    if area in ('all', 'weather'):
        weather_api.cache_clear('weather')
    if area in ('all', 'geocode'):
        try:
            geocoder._geocode_cache.clear()
        except Exception:
            pass

    return {"status": "ok", "cleared": area}


@app.get("/api/cache/status")
async def api_cache_status(token: str = None, request: Request = None):
    """Return basic cache status; protected by same admin token."""
    # Use permissive helper: allows localhost or env override for dev
    if not _is_admin_authorized(request):
        raise HTTPException(status_code=403, detail="Forbidden")

    status = weather_api.cache_status()
    try:
        geo_keys = len(geocoder._geocode_cache.keys())
    except Exception:
        geo_keys = None
    status['geocode_cache_keys'] = geo_keys
    return status


@app.get('/api/forecast')
async def api_forecast(city: str = None, days: int = 5):
    """Return daily forecast for a city (basic fields)."""
    if not city or not city.strip():
        raise HTTPException(status_code=400, detail='city parameter is required')
    try:
        coords = get_coordinates(city)
    except GeocodingNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except GeocodingError as e:
        raise HTTPException(status_code=503, detail=str(e))

    try:
        data = weather_api.get_forecast(coords['latitude'], coords['longitude'], days=int(days))
        return JSONResponse({'status': 'ok', 'data': data})
    except WeatherAPIError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
