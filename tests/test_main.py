from main import get_weather_by_city
import pytest

class DummyWeather:
    def __init__(self, temp):
        self.temperature = temp
    def __str__(self):
        return f"Dummy {self.temperature}"


def test_get_weather_by_city_invalid():
    with pytest.raises(ValueError):
        get_weather_by_city('')
    with pytest.raises(ValueError):
        get_weather_by_city(None)


def test_get_weather_by_city_flow(monkeypatch):
    # patchare le funzioni e la classe importate dentro il modulo `main`
    monkeypatch.setattr('main.get_coordinates', lambda name: {'latitude': 45.0, 'longitude': 9.0})
    monkeypatch.setattr('main.get_weather', lambda lat, lon: {'current_weather': {'temperature': 5}})
    monkeypatch.setattr('main.Weather', lambda data: DummyWeather(data['current_weather']['temperature']))

    w = get_weather_by_city('Milano')
    assert w is not None
    assert hasattr(w, 'temperature')
    assert w.temperature == 5
