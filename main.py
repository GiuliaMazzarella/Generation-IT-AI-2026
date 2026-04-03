# main.py
"""
Applicazione CLI per ricavare il meteo attuale di una città.

Il modulo fornisce:
- `get_weather_by_city(city_name)`: funzione che esegue geocoding e
  interroga l'API meteo per restituire un oggetto `Weather`.
- `main()`: loop interattivo CLI che legge `input()` dall'utente e mostra
  i risultati.

Esempio d'uso (da riga di comando):
    >>> python main.py
    === 🌦️ APP METEO ===
    Inserisci il nome di una città (es: Milano, Roma, Paris). Digita 'exit' per uscire.
    Città: Milano
    \n🌤️ Meteo attuale:\nTemperatura: 12°C\n...

Note:
- Le funzioni di basso livello possono sollevare eccezioni custom definite
  in `exceptions.py` (es. `GeocodingError`, `WeatherAPIError`). Il `main()`
  gestisce queste eccezioni per mostrare messaggi user-friendly.
"""

import logging
import os
import sys
from utils.geocoder import get_coordinates
from api.weather_api import get_weather
from models.weather_model import Weather
from exceptions import GeocodingError, GeocodingNotFoundError, WeatherAPIError, InvalidCoordinatesError
from metrics import get_metrics, log_metrics

# Ridotto livello di logging per ridurre I/O e consumo energetico
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def request_user_consent(input_fn=None, print_fn=print) -> bool:
    """Ask the user for consent before sending the city name to external services."""
    preset = os.getenv('WEATHER_USER_CONSENT', '').strip().lower()
    if preset in ('1', 'true', 'yes', 'y', 's', 'si'):
        return True
    if preset in ('0', 'false', 'no', 'n'):
        return False

    # In automated or non-interactive contexts, assume the caller manages consent explicitly.
    try:
        if not sys.stdin or not sys.stdin.isatty():
            return True
    except Exception:
        return True

    if input_fn is None:
        input_fn = input

    print_fn("Privacy: per cercare il meteo, il nome della città verrà inviato ai servizi Open-Meteo e Nominatim.")
    print_fn("Le cache persistenti sono disattivate di default; abilitarle è una scelta esplicita dell'utente.")

    while True:
        try:
            answer = input_fn("Acconsenti al trattamento minimo dei dati necessari? (s/n): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print_fn("\nConsenso non fornito. Uscita.")
            return False

        if answer in ('s', 'si', 'y', 'yes'):
            return True
        if answer in ('n', 'no'):
            print_fn("Consenso negato. Nessuna richiesta verrà inviata ai servizi esterni.")
            return False

        print_fn("Risposta non valida. Inserisci 's' oppure 'n'.")


def get_weather_by_city(city_name: str):
    """
    Ottiene il meteo corrente per una città.

    Args:
        city_name: Nome della città (stringa non vuota).

    Returns:
        Istanza di `Weather` contenente i dati estratti dall'API.

    Raises:
        ValueError: se l'input non è una stringa valida.
        GeocodingError/GeocodingNotFoundError: se la geocodifica fallisce.
        InvalidCoordinatesError/WeatherAPIError: per problemi con l'API meteo.

    Example:
        >>> get_weather_by_city('Milano')
        <models.weather_model.Weather object>
    """
    # Controllo input
    if not isinstance(city_name, str) or not city_name.strip():
        raise ValueError("Inserisci un nome di città valido")

    # Geocodifica (può sollevare GeocodingError / GeocodingNotFoundError)
    coords = get_coordinates(city_name)

    # Chiamata API (può sollevare InvalidCoordinatesError / WeatherAPIError)
    data = get_weather(coords["latitude"], coords["longitude"])

    # Creazione modello
    weather = Weather(data)
    return weather


def main():
    """
    Loop CLI interattivo.

    Non prende argomenti e gestisce l'interazione utente tramite `input()` e
    `print()`. Gestisce eccezioni custom e permette all'utente di ripetere le
    ricerche fino a quando non sceglie di uscire.
    """
    print("=== 🌦️ APP METEO ===")
    print("Inserisci il nome di una città (es: Milano, Roma, Paris). Digita 'exit' per uscire.\n")

    if not request_user_consent():
        return

    try:
        while True:
            city = input("Città: ").strip()

            # Permetti all'utente di uscire
            if city.lower() in ("exit", "quit"):
                print("Uscita.")
                break

            # Input vuoto -> riprova
            if not city:
                print("⚠️ Inserisci un nome di città valido (es. Milano)")
                continue

            try:
                weather = get_weather_by_city(city)
            except GeocodingNotFoundError:
                print("❌ Città non trovata. Riprova.")
                weather = None
            except GeocodingError:
                print("❌ Errore durante la geocodifica. Riprova più tardi.")
                weather = None
            except InvalidCoordinatesError:
                print("❌ Coordinate non valide per la città trovata.")
                weather = None
            except WeatherAPIError:
                print("❌ Errore nel recupero dei dati meteo.")
                weather = None
            except ValueError:
                print("⚠️ Inserisci un nome di città valido (es. Milano)")
                weather = None
            except Exception:
                print("Si è verificato un errore imprevisto. Riprova.")
                weather = None

            if weather:
                print(weather)

            # Chiedi all'utente se vuole riprovare o uscire
            while True:
                try:
                    ans = input("Vuoi cercarne un'altra? (s/n): ").strip().lower()
                except (KeyboardInterrupt, EOFError):
                    ans = 'n'
                if ans in ('s', 'si', 'y', 'yes'):
                    # continua il loop principale
                    print()
                    break
                if ans in ('n', 'no', 'quit', 'exit'):
                    print("Uscita.")
                    return
                # risposta non valida -> richiedi di nuovo
                print("Risposta non valida. Inserisci 's' per sì oppure 'n' per no.")

    except (KeyboardInterrupt, EOFError):
        # Gestione ctrl-C / ctrl-D
        print("\nUscita.")

    finally:
        # Se la variabile d'ambiente WEATHER_METRICS è impostata, logga le metriche
        try:
            if os.getenv('WEATHER_METRICS', '0') == '1':
                print('\nMetriche raccolte:')
                log_metrics(logger)
        except Exception:
            pass


if __name__ == "__main__":
    main()