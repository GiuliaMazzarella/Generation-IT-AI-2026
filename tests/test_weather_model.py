from models.weather_model import Weather


def test_weather_model_parsing():
    data = {
        'current_weather': {
            'temperature': 12,
            'windspeed': 3,
            'winddirection': 270,
            'time': '2026-03-18T09:00'
        }
    }
    w = Weather(data)
    assert w.temperature == 12
    assert w.windspeed == 3
    assert w.winddirection == 270
    assert w.time == '2026-03-18T09:00'
    s = str(w)
    assert 'Temperatura' in s or '12' in s


def test_weather_model_empty():
    w = Weather({})
    assert w.temperature is None
    assert w.windspeed is None
    assert w.winddirection is None
    assert w.time is None
