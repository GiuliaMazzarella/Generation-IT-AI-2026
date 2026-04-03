"""
exceptions.py
Definizione di eccezioni custom per il progetto Weather App.

Questo modulo definisce eccezioni specifiche che vengono usate per
segnalare problemi a livello di geocodifica, API meteo e validazione delle
coordinate. I moduli che chiamano funzioni come `get_coordinates` o
`get_weather` possono intercettare queste eccezioni per mostrare messaggi
user-friendly o per decidere una strategia di retry.

Esempio:
    >>> from exceptions import GeocodingNotFoundError
    >>> try:
    ...     get_coordinates('CittàInesistente')
    ... except GeocodingNotFoundError:
    ...     print('Città non trovata')

"""

class WeatherAppError(Exception):
    """Base class per eccezioni dell'app meteo."""
    pass

class GeocodingError(WeatherAppError):
    """Errore durante la geocodifica (network, servizio, ecc.)."""
    pass

class GeocodingNotFoundError(GeocodingError):
    """La città richiesta non è stata trovata dal geocoder."""
    pass

class WeatherAPIError(WeatherAppError):
    """Errore durante la chiamata all'API meteo (HTTP, parsing, ecc.)."""
    pass

class InvalidCoordinatesError(WeatherAppError):
    """Coordinate non valide fornite a `get_weather`."""
    pass
