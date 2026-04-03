# models/weather_model.py
"""
Model per rappresentare i dati meteo restituiti da Open-Meteo.

La classe `Weather` prende il payload JSON restituito dall'API e estrae i campi
più utili (temperatura, velocità del vento, direzione, timestamp).

Esempio:
    >>> from models.weather_model import Weather
    >>> w = Weather({'current_weather': {'temperature': 12, 'windspeed': 3, 'winddirection': 270, 'time': '2026-03-18T09:00'}})
    >>> str(w)
    "\n🌤️ Meteo attuale:\nTemperatura: 12°C\n..."
"""

from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class Weather:
    """
    Rappresenta il meteo corrente per una posizione.

    Args:
        data: dizionario JSON restituito dall'API Open-Meteo. Può contenere la chiave speciale `_meta` con informazioni su sorgente e age.

    Attributi:
        temperature (Optional[float]): temperatura corrente in °C.
        windspeed (Optional[float]): velocità del vento in km/h.
        winddirection (Optional[float]): direzione del vento in gradi.
        time (Optional[str]): timestamp della lettura.

    Example:
        >>> w = Weather({'current_weather': {'temperature': 12}})
        >>> w.temperature
        12
    """
    def __init__(self, data: Dict[str, Any]):
        """
        Estrae solo i dati utili dalla risposta API.
        Se la struttura non è quella attesa, valorizza gli attributi a None e logga.
        """
        try:
            if not isinstance(data, dict):
                raise TypeError("Data must be a dict")

            # supporto per metadata: data may contain '_meta'
            meta = data.get('_meta', {}) if isinstance(data, dict) else {}
            self.source = meta.get('source')
            self.age_seconds = meta.get('age_seconds')

            current = data.get("current_weather") or {}

            self.temperature = current.get("temperature")
            self.windspeed = current.get("windspeed")
            self.winddirection = current.get("winddirection")
            self.time = current.get("time")

        except Exception:
            logger.exception("Errore durante la creazione del modello Weather")
            self.temperature = None
            self.windspeed = None
            self.winddirection = None
            self.time = None
            self.source = None
            self.age_seconds = None

    def _fmt(self, value: Optional[Any], suffix: str = "") -> str:
        return f"{value}{suffix}" if value is not None else "N/D"

    def __str__(self):
        source_note = ''
        if self.source == 'stale':
            try:
                hours = int(self.age_seconds) // 3600 if self.age_seconds is not None else None
                source_note = f" (dati offline, aggiornati ~{hours} ore fa)" if hours is not None else " (dati offline)"
            except Exception:
                source_note = " (dati offline)"
        elif self.source == 'cached':
            source_note = " (cache)"
        elif self.source == 'live':
            source_note = ""

        return (
            f"\n🌤️ Meteo attuale:{source_note}\n"
            f"Temperatura: {self._fmt(self.temperature, '°C')}\n"
            f"Vento: {self._fmt(self.windspeed, ' km/h')}\n"
            f"Direzione vento: {self._fmt(self.winddirection, '°')}\n"
            f"Ora rilevazione: {self._fmt(self.time)}\n"
        )