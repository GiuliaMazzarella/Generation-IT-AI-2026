"""
metrics.py
Semplice modulo per raccogliere metriche di chiamate esterne.

Fornisce contatori thread-safe (semplice Lock) per tracciare il numero di
richieste fatte al geocoder e all'API meteo, e il numero di chiamate esterne
(esecuzioni reali, non-cache).

API:
- inc_counter(name): incrementa un contatore
- get_metrics(): ritorna copia dei contatori
- reset_metrics(): azzera i contatori
- log_metrics(logger=None): scrive le metriche su logger.info o stampa su stdout

Questa implementazione è intenzionalmente minimale e adatta all'uso CLI.
Per ambienti di produzione si consiglia una soluzione esterna (Prometheus, etc.).
"""
from threading import Lock
from typing import Dict
import logging

_lock = Lock()
_counters: Dict[str, int] = {}


def inc_counter(name: str, amount: int = 1) -> None:
    """Incrementa il contatore `name` di `amount`."""
    with _lock:
        _counters[name] = _counters.get(name, 0) + int(amount)


def get_metrics() -> Dict[str, int]:
    """Ritorna una copia dei contatori raccolti."""
    with _lock:
        return dict(_counters)


def reset_metrics() -> None:
    """Azzera tutti i contatori."""
    with _lock:
        _counters.clear()


def log_metrics(logger: logging.Logger = None) -> None:
    """Logga le metriche via logger.info (se fornito) o su stdout."""
    metrics = get_metrics()
    if logger is None:
        print("METRICS:")
        for k, v in sorted(metrics.items()):
            print(f"  {k}: {v}")
    else:
        logger.info("METRICS: %s", metrics)
