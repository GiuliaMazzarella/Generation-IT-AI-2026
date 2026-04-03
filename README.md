# Weather App v1.1

Una semplice applicazione CLI Python per ottenere il meteo attuale di una città usando la geocodifica (Nominatim via geopy) e l'API Open‑Meteo.

Questo repository contiene il codice sorgente, test (unitari e di integrazione separati) e le istruzioni per eseguire l'app e i test in locale.

Indice
- Panoramica
- Requisiti
- Installazione
- Guida all'utilizzo
- Interfaccia web (API e endpoint)
- Esempio di output
- Funzionalità
- Gestione degli errori
- API esterne utilizzate
- Test (unitari e di integrazione)
- Miglioramenti futuri
- Contribuire

Panoramica
---------
L'app richiede il nome di una città, ottiene le coordinate geografiche tramite Nominatim (geopy) e poi interroga Open‑Meteo per ottenere il meteo attuale. I dati vengono incapsulati in un oggetto `Weather` e mostrati in console.

Requisiti
---------
- Python 3.8+
- Connessione Internet per la geocodifica e le chiamate all'API (se si eseguono le richieste reali)

I pacchetti principali sono elencati in `requirements.txt` e quelli per lo sviluppo in `requirements-dev.txt`.

Installazione
------------
Esempio di setup rapido (PowerShell su Windows):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r .\requirements.txt
python -m pip install -r .\requirements-dev.txt
```

Guida all'utilizzo
-----------------
Per avviare l'app in modalità interattiva da terminale:

```powershell
.\.venv\Scripts\Activate.ps1
python .\main.py
```

Comportamento principale:
- L'app stampa un'intestazione e richiede il nome della città.
- Inserire il nome della città (es: Milano, Roma, Paris). Digita `exit` o `quit` per uscire.
- Se la città è valida e le chiamate a rete vanno a buon fine, verrà mostrato il meteo attuale.
- Dopo ogni ricerca viene chiesto se vuoi cercarne un'altra (s/n). Rispondi `s` o `n`.

Interfaccia web (API e endpoint)
-------------------------------
Questa versione include anche una semplice interfaccia web basata su FastAPI che espone una pagina HTML e alcuni endpoint JSON riutilizzabili dalla UI o da script.

Eseguire il server (PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app:app --reload --port 8000
```

Endpoint principali (tabella)

| Endpoint | Metodo | Descrizione | Autenticazione |
|---|---:|---|---|
| `/` | GET | Pagina web interattiva (UI) per cercare il meteo | nessuna |
| `/api/weather?city={nome}` | GET | Ritorna JSON con i dati del meteo per la città richiesta. Response: `200 { "status": "ok", "data": ... }` oppure 4xx/5xx | nessuna |
| `/api/health` | GET | Health check: `{ "status": "ok" }` | nessuna |

Endpoint di gestione cache (protetti)
------------------------------------

| Endpoint | Metodo | Descrizione | Autenticazione |
|---|---:|---|---|
| `/api/cache/status` | GET | Ritorna informazioni sintetiche sulla cache (numero di chiavi). | header `x-admin-token` obbligatorio |
| `/api/cache/clear?area={all\|weather\|geocode}` | POST | Cancella la cache specificata (default `all`). | header `x-admin-token` obbligatorio |

Admin token (variabili d'ambiente e cifratura)
---------------------------------------------
Per maggiore sicurezza, il token amministrativo viene ora letto **prima di tutto** dalla variabile d'ambiente `WEATHER_ADMIN_TOKEN`.

PowerShell:

```powershell
$env:WEATHER_ADMIN_TOKEN = 'sostituisci-con-un-token-lungo-e-casuale'
```

Se vuoi anche una persistenza locale **cifrata**, imposta una chiave Fernet in `WEATHER_ENCRYPTION_KEY`:

```powershell
$env:WEATHER_ENCRYPTION_KEY = (& .\.venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

Comportamento attuale:
- `WEATHER_ADMIN_TOKEN` presente -> usato direttamente (modalità raccomandata)
- `WEATHER_ENCRYPTION_KEY` presente -> eventuale token locale salvato in `.admin_token.enc` cifrato
- nessuna variabile presente -> viene generato un token temporaneo in memoria valido solo per il processo corrente

Attenzione di sicurezza:
- Non committare mai `.env`, `.admin_token`, `.admin_token.enc` o file cache nel repository.
- In produzione usa un secret manager o variabili d'ambiente del servizio.

Sblocco rapido per sviluppo (opzionale)
-------------------------------------
Se durante lo sviluppo hai problemi ad aprire la UI a causa del controllo del token amministrativo, puoi abilitare una modalità più permissiva (solo per uso locale) impostando la variabile d'ambiente `WEATHER_ALLOW_WEAK_ADMIN=1` prima di avviare il server. In questa modalità le richieste provenienti da localhost saranno permesse anche senza header `x-admin-token`.

PowerShell (solo per sviluppo locale):

```powershell
$env:WEATHER_ALLOW_WEAK_ADMIN = '1'
uvicorn app:app --reload --port 8000
```

Usa questa opzione solo in ambienti di sviluppo o quando sei sicuro che l'accesso alla macchina sia controllato. Non abilitare questa variabile in produzione.

Esempio (curl) per cache status:

```bash
curl -H "x-admin-token: <TOKEN>" http://127.0.0.1:8000/api/cache/status
```

Per configurare il token amministrativo impostare la variabile d'ambiente `WEATHER_ADMIN_TOKEN` prima di avviare il server (sostituisci `<TOKEN>` con un valore sicuro):

PowerShell:

```powershell
$env:WEATHER_ADMIN_TOKEN = 'mio-token-segreto'
uvicorn app:app --reload --port 8000
```

Note:
- La UI risiede in `templates/index.html` e le risorse statiche in `static/`.
- Gli endpoint usano la stessa logica di business del CLI (geocoding, cache, fallback offline).

Esempio di output
-----------------
Esempio di sessione (esempio reale):

=== 🌦️ APP METEO ===
Inserisci il nome di una città (es: Milano, Roma, Paris). Digita 'exit' per uscire.

Città: Milano

🌤️ Meteo attuale:
Temperatura: 14.3°C
Vento: 5.4 km/h
Direzione vento: 230°
Ora rilevazione: 2026-03-19T12:00:00Z

Vuoi cercarne un'altra? (s/n): n
Uscita.

(se l'utente inserisce una città non trovata):

Città: 347f
❌ Città non trovata. Riprova.
Vuoi cercarne un'altra? (s/n): s

Funzionalità
-----------
- Interfaccia CLI minimalista per cercare il meteo per città.
- Geocoding con Nominatim (geopy).
- Chiamata all'API Open‑Meteo con timeout e gestione degli errori HTTP/JSON.
- Modello `Weather` che normalizza e formatta l'output.
- Test unitari che usano monkeypatch per isolare le chiamate di rete.
- Test di integrazione separati in `integration_tests/` (marcati con `@pytest.mark.integration`).

Gestione degli errori
---------------------
L'app gestisce diversi casi di errore in modo informativo:
- Input non valido o vuoto -> messaggio e richiesta di reinserimento.
- Geocodifica fallita (città non trovata o errore) -> messaggio "❌ Città non trovata. Riprova." e ritorno al prompt se l'utente vuole riprovare.
- Errore nella chiamata API (timeout, rete o errore HTTP) -> messaggio "❌ Errore nel recupero dei dati meteo.".
- Parsing JSON fallito -> viene segnalato e l'app non va in crash.
- Gestione di KeyboardInterrupt/EOFError (Ctrl+C / Ctrl+D) che chiude l'app pulitamente.

Dettagli tecnici e API esterne
------------------------------
- Geocoding: Nominatim attraverso la libreria `geopy`. Nella funzione `get_coordinates` viene usato `Nominatim(user_agent="weather_app")` con timeout di 10 secondi.
- Meteo: Open‑Meteo (https://open-meteo.com) — endpoint configurato in `config.py` con `BASE_URL` e `DEFAULT_PARAMS` (al momento `current_weather: True`).
- HTTP: richieste effettuate con `requests` (timeout 10s).

File principali
---------------
- `main.py` — entrypoint CLI e loop interattivo.
- `utils/geocoder.py` — funzione `get_coordinates(city_name)`.
- `api/weather_api.py` — funzione `get_weather(latitude, longitude)`.
- `models/weather_model.py` — classe `Weather` che normalizza la risposta.
- `config.py` — URL e parametri di default per l'API.
- `tests/` — test unitari.
- `integration_tests/` — test di integrazione (marcati `integration`).

Test (unitari e integrazione)
----------------------------
- I test unitari sono nel folder `tests/` e dovrebbero poter essere eseguiti senza accesso rete grazie all'uso di monkeypatch.
- I test di integrazione sono separati in `integration_tests/` e marcati con `@pytest.mark.integration`.

Il file `pytest.ini` nel progetto ha la seguente configurazione di default:
```
addopts = -m "not integration"
```
Questo significa che i test di integrazione vengono esclusi di default. Per eseguirli esplicitamente:

```powershell
.\.venv\Scripts\Activate.ps1
pytest -q integration_tests/ -m integration
```

Se desideri disabilitare temporaneamente o modificare il comportamento dei test di integrazione, puoi modificare `pytest.ini` o la marcatura nel file corrispondente.

Miglioramenti futuri
--------------------
- Migliorare il parsing dell'output per includere previsioni orarie/giornaliere.
- Caching delle risposte di geocoding per ridurre le chiamate a Nominatim.
- Aggiungere gestione dei rate limit e retry esponenziale per chiamate di rete.
- Interfaccia web minima (Flask/FastAPI) per visualizzare i dati in pagina.
- Migliorare i messaggi internazionali (i18n) e i test di UI.

Miglioramenti eco-friendly e metriche
------------------------------------
Per ridurre l'impatto delle chiamate di rete e il consumo computazionale sono state introdotte alcune modifiche:

- Retry ridotti: il numero di retry HTTP nelle chiamate a Open‑Meteo è ora ridotto (1 retry) per limitare ripetute richieste in caso di errori transitori. Puoi modificare questo comportamento in `api/weather_api.py` nella funzione `_get_session_with_retries()`.

- Caching LRU per Open‑Meteo: le risposte meteo vengono memorizzate in una cache LRU in memoria (`api.weather_api._get_weather_cached`) usando coordinate arrotondate (precisione predefinita: 3 decimali). Questo evita chiamate duplicate per coordinate molto vicine. Per cambiare la precisione, modifica la funzione `_round_coords` in `api/weather_api.py`.

- Logging ridotto: il livello di logging di default è impostato a `WARNING` per limitare l'I/O e il rumore di log. Puoi ripristinare `INFO` impostando `logging.basicConfig(level=logging.INFO, ...)` in `main.py` o impostando il logger globalmente.

- Metriche opzionali: è stato aggiunto un semplice sistema di metriche in `metrics.py` che traccia:
  - `geocoder.total_requests` — numero totale di chiamate al geocoder (inclusi cache hit)
  - `geocoder.uncached_requests` — numero di chiamate uncached al geocoder
  - `weather_api.total_requests` — numero totale di richieste meteo (incl. cache hits)
  - `weather_api.uncached_requests` — numero di richieste uncached all'API meteo

  Per abilitare la stampa delle metriche al termine dell'esecuzione impostare la variabile d'ambiente `WEATHER_METRICS=1` prima di avviare l'app:

  Esempio PowerShell:

  ```powershell
  $env:WEATHER_METRICS = '1'
  python .\main.py
  ```

  Output di esempio (stampato all'uscita):
  ```text
  Metriche raccolte:
    geocoder.total_requests: 3
    geocoder.uncached_requests: 2
    weather_api.total_requests: 2
    weather_api.uncached_requests: 1
  ```

Note sulla configurabilità
- Le impostazioni principali (retry count, cache precision) sono attualmente codificate in `api/weather_api.py`. Se preferisci una configurazione più dinamica, possiamo introdurre variabili in `config.py` (es. `RETRY_TOTAL`, `CACHE_PRECISION`) e leggere tali valori nel modulo API.

Raccomandazione
- Se esegui l'app in produzione o in ambienti condivisi, valuta di sostituire la cache in memoria con una soluzione persistente (Redis, diskcache) e di inviare le metriche a un sistema di monitoring (Prometheus, DataDog) invece di stamparle su stdout.

Compliance, licenze e privacy
-----------------------------
Per verificare i tre aspetti principali di conformità:

1. **Segreti in variabili d'ambiente**
   - usa `WEATHER_ADMIN_TOKEN`
   - usa `WEATHER_ENCRYPTION_KEY` per la persistenza cifrata locale
2. **Licenze terze parti**
   - esegui `./.venv/Scripts/python.exe .\tools\check_licenses.py --fail-on-unknown`
   - consulta `THIRD_PARTY_LICENSES.md`
3. **Dati utente e consenso**
   - la UI richiede consenso esplicito prima delle ricerche
   - la CLI chiede consenso prima della prima chiamata esterna
   - la cache persistente è disattivata di default; vedi `PRIVACY.md`

Contribuire
-----------
1. Fork e crea un branch.
2. Aggiungi test per la tua modifica.
3. Apri una pull request descrivendo le modifiche.

Licenza
-------
File sorgente fornito senza una licenza esplicita — aggiungi eventualmente una LICENCE se necessario.

Contatti
--------
Per domande o richieste particolari, apri un issue nel repository o contatta l'autore del progetto.
