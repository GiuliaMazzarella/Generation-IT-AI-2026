import requests
import pytest
from api import weather_api
from exceptions import WeatherAPIError

class DummyResponse:
    def __init__(self, status_code, json_data=None):
        self.status_code = status_code
        self._json_data = json_data or {}
    def json(self):
        return self._json_data


def test_get_weather_success(monkeypatch):
    # Clear caches to avoid interference across tests
    weather_api._get_weather_cached.cache_clear()
    try:
        weather_api._cache_api.clear()
    except Exception:
        pass

    def fake_get(url, params=None, timeout=None):
        return DummyResponse(200, {"current_weather": {"temperature": 10}})
    monkeypatch.setattr('api.weather_api._get_session_with_retries', lambda: type('S', (), {'get': staticmethod(fake_get)})())
    data = weather_api.get_weather(45.0, 9.0)
    assert isinstance(data, dict)
    assert 'current_weather' in data


def test_get_weather_http_error(monkeypatch):
    weather_api._get_weather_cached.cache_clear()
    try:
        weather_api._cache_api.clear()
    except Exception:
        pass

    def fake_get(url, params=None, timeout=None):
        return DummyResponse(500)
    monkeypatch.setattr('api.weather_api._get_session_with_retries', lambda: type('S', (), {'get': staticmethod(fake_get)})())
    with pytest.raises(WeatherAPIError):
        weather_api.get_weather(45.0, 9.0)


def test_get_weather_exception(monkeypatch):
    weather_api._get_weather_cached.cache_clear()
    try:
        weather_api._cache_api.clear()
    except Exception:
        pass

    def fake_get(url, params=None, timeout=None):
        raise requests.exceptions.RequestException("boom")
    monkeypatch.setattr('api.weather_api._get_session_with_retries', lambda: type('S', (), {'get': staticmethod(fake_get)})())
    with pytest.raises(WeatherAPIError):
        weather_api.get_weather(45.0, 9.0)
