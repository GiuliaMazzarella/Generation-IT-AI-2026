"""
Simple cache with TTL and optional disk persistence for offline fallback.

Provides a minimal API used by the project to store cached responses with
timestamps, serve stale data when fetch fails (offline scenario) and persist
cache to disk to survive process restarts.

Usage:
    cache = SimpleCache('.cache_file.pkl')
    value = cache.get_or_fetch(key, fetch_func, ttl=300, stale_ttl=86400)

Methods:
- get(key, max_age=None)
- set(key, value)
- get_or_fetch(key, fetch_func, ttl=None, stale_ttl=None)
- clear()

This implementation uses `pickle` for persistence and is thread-safe.
"""
import os
import time
import pickle
from threading import Lock
from typing import Any, Callable, Dict, Optional


class SimpleCache:
    def __init__(self, cache_file: Optional[str] = None):
        self._cache_file = cache_file
        self._lock = Lock()
        # internal store: key -> (value, timestamp)
        self._store: Dict[str, Any] = {}
        if cache_file:
            self._load()

    def _load(self) -> None:
        try:
            if os.path.exists(self._cache_file):
                with open(self._cache_file, 'rb') as f:
                    self._store = pickle.load(f)
        except Exception:
            # ignore load errors
            self._store = {}

    def _save(self) -> None:
        try:
            if not self._cache_file:
                return
            tmp = f"{self._cache_file}.tmp"
            with open(tmp, 'wb') as f:
                pickle.dump(self._store, f)
            os.replace(tmp, self._cache_file)
        except Exception:
            # ignore save errors to avoid crashing app
            pass

    def get(self, key: str, max_age: Optional[float] = None) -> Optional[Any]:
        """Return value if present and not older than max_age (seconds).
        If max_age is None returns value regardless of age.
        """
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            value, ts = item
            if max_age is None:
                return value
            if (time.time() - ts) <= float(max_age):
                return value
            return None

    def get_with_age(self, key: str) -> Optional[tuple]:
        """Return (value, age_seconds) if present, otherwise None."""
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            value, ts = item
            return (value, time.time() - ts)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = (value, time.time())
            # persist
            self._save()

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._save()

    def get_or_fetch(self, key: str, fetch_func: Callable[[], Any], ttl: Optional[float] = None, stale_ttl: Optional[float] = None) -> Any:
        """
        Try to fetch fresh value calling `fetch_func`. If fetch succeeds store and return it.
        If fetch raises, return cached value if available and not older than `stale_ttl`.
        Otherwise re-raise the exception from fetch_func.
        """
        try:
            result = fetch_func()
            # store result
            self.set(key, result)
            return result
        except Exception as e:
            # fetch failed -> try to return stale
            if stale_ttl is not None:
                with self._lock:
                    item = self._store.get(key)
                    if item:
                        value, ts = item
                        if (time.time() - ts) <= float(stale_ttl):
                            return value
            # no stale available -> re-raise
            raise

    def keys(self):
        with self._lock:
            return list(self._store.keys())
