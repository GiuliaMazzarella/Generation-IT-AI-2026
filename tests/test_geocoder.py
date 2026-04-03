from utils import geocoder
import pytest

class DummyLocation:
    def __init__(self, lat, lon):
        self.latitude = lat
        self.longitude = lon

class DummyGeolocator:
    def geocode(self, name, timeout=None):
        if name.lower() == "milano":
            return DummyLocation(45.4642, 9.1900)
        return None


def test_get_coordinates_success(monkeypatch):
    """get_coordinates dovrebbe ritornare le coordinate per una città valida"""
    geocoder._geocode_cached.cache_clear()
    try:
        geocoder._geocode_cache.clear()
    except Exception:
        pass

    monkeypatch.setattr('utils.geocoder.Nominatim', lambda user_agent: DummyGeolocator())
    coords = geocoder.get_coordinates('Milano')
    assert coords == {"latitude": 45.4642, "longitude": 9.1900}


def test_get_coordinates_not_found(monkeypatch):
    """get_coordinates dovrebbe sollevare GeocodingNotFoundError per città non trovata"""
    geocoder._geocode_cached.cache_clear()
    try:
        geocoder._geocode_cache.clear()
    except Exception:
        pass

    monkeypatch.setattr('utils.geocoder.Nominatim', lambda user_agent: DummyGeolocator())
    with pytest.raises(Exception):
        geocoder.get_coordinates('CittàInesistente')
