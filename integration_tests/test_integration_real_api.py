import pytest
from utils.geocoder import get_coordinates
from api.weather_api import get_weather

@pytest.mark.integration
def test_real_pipeline_milano():
    """
    Test di integrazione reale: geocodifica con Nominatim e chiamata a Open-Meteo.
    Questo file si trova in `integration_tests/` per tenerlo separato dai test unitari.
    Per eseguirlo:
      - rimuovi lo skip se presente (non c'è qui),
      - o esegui `pytest -q -m integration`.
    """
    coords = get_coordinates('Milano')
    assert coords is not None
    assert 'latitude' in coords and 'longitude' in coords

    data = get_weather(coords['latitude'], coords['longitude'])
    assert data is not None
    assert isinstance(data, dict)
    assert 'current_weather' in data
