import requests

url = 'http://127.0.0.1:8001/api/health'

try:
    r = requests.get(url, timeout=5)
    r.raise_for_status()
    print("Status:", r.status_code)
    try:
        print("JSON:", r.json())
    except ValueError:
        print("Body (non JSON):", r.text)
except requests.exceptions.Timeout:
    print("ERRORE: Timeout: il server non ha risposto entro 5 secondi.")
except requests.exceptions.ConnectionError as e:
    print("ERRORE: ConnectionError: impossibile connettersi (server non avviato / porta errata / firewall).")
    print("Dettaglio:", e)
except requests.exceptions.HTTPError as e:
    print("ERRORE HTTP:", e)
    print("Body:", getattr(e.response, 'text', None))
except Exception as e:
    print("Other error:", e)
