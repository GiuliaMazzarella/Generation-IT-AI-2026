import requests
import pytest
from api import weather_api
from exceptions import WeatherAPIError

class DummyResponse:
    def __init__(self, status_code, json_data=None, raise_on_json=False):
        self.status_code = status_code
        self._json_data = json_data
        self._raise_on_json = raise_on_json
    def json(self):
        if self._raise_on_json:
            raise ValueError("Invalid JSON")
        return self._json_data


def test_get_weather_malformed_json(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        return DummyResponse(200, json_data=None, raise_on_json=True)
    monkeypatch.setattr('api.weather_api._get_session_with_retries', lambda: type('S', (), {'get': staticmethod(fake_get)})())

    with pytest.raises(WeatherAPIError):
        weather_api.get_weather(45.0, 9.0)


def test_get_weather_missing_current_weather(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        return DummyResponse(200, json_data={})
    monkeypatch.setattr('api.weather_api._get_session_with_retries', lambda: type('S', (), {'get': staticmethod(fake_get)})())

    data = weather_api.get_weather(45.0, 9.0)
    assert isinstance(data, dict)
    assert 'current_weather' not in data
