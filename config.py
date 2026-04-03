# config.py

import os
import secrets
from typing import Optional

try:
    from cryptography.fernet import Fernet, InvalidToken
except Exception:  # pragma: no cover - optional dependency fallback
    Fernet = None
    InvalidToken = Exception

# URL API Open-Meteo
BASE_URL = "https://api.open-meteo.com/v1/forecast"

# Parametri di default
DEFAULT_PARAMS = {
    "current_weather": True
}

# Caching e comportamento eco-friendly
CACHE_TTL = 300             # seconds: consider data fresh for this many seconds
CACHE_STALE_TTL = 86400     # seconds: consider stale but usable up to this
CACHE_PRECISION = 3         # decimals for rounding coordinates (cache key)
PERSISTENT_CACHE_ENABLED = os.getenv("WEATHER_ENABLE_PERSISTENT_CACHE", "0").strip().lower() in {"1", "true", "yes", "y", "on"}

# Retry behavior
RETRY_TOTAL = 1
RETRY_BACKOFF = 0.2

# Negative cache TTL (per geocoder 'not found')
NEGATIVE_CACHE_TTL = 86400  # 1 day

# Security / secrets configuration
ADMIN_TOKEN_ENV_VAR = "WEATHER_ADMIN_TOKEN"
ENCRYPTION_KEY_ENV_VAR = "WEATHER_ENCRYPTION_KEY"
_admin_token_file = os.path.join(os.path.dirname(__file__), '.admin_token.enc')
_legacy_admin_token_file = os.path.join(os.path.dirname(__file__), '.admin_token')


def _read_text_file(path: str) -> Optional[str]:
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                value = f.read().strip()
                return value or None
    except Exception:
        return None
    return None


def _get_fernet() -> Optional[Fernet]:
    raw_key = os.getenv(ENCRYPTION_KEY_ENV_VAR, '').strip()
    if not raw_key or Fernet is None:
        return None
    try:
        return Fernet(raw_key.encode('utf-8'))
    except Exception:
        return None


def _load_admin_token() -> str:
    """Load the admin token securely.

    Priority order:
    1. `WEATHER_ADMIN_TOKEN` environment variable (recommended)
    2. encrypted `.admin_token.enc` file if `WEATHER_ENCRYPTION_KEY` is configured
    3. legacy plain-text `.admin_token` (migration only, read-only)
    4. ephemeral random token in memory for the current process
    """
    env_token = os.getenv(ADMIN_TOKEN_ENV_VAR, '').strip()
    if env_token:
        return env_token

    fernet = _get_fernet()
    if fernet and os.path.exists(_admin_token_file):
        try:
            with open(_admin_token_file, 'rb') as f:
                encrypted = f.read()
            token = fernet.decrypt(encrypted).decode('utf-8').strip()
            if token:
                return token
        except (OSError, InvalidToken, ValueError):
            pass

    legacy_token = _read_text_file(_legacy_admin_token_file)
    if legacy_token:
        if fernet:
            try:
                with open(_admin_token_file, 'wb') as f:
                    f.write(fernet.encrypt(legacy_token.encode('utf-8')))
            except OSError:
                pass
        return legacy_token

    generated = secrets.token_urlsafe(32)
    if fernet:
        try:
            with open(_admin_token_file, 'wb') as f:
                f.write(fernet.encrypt(generated.encode('utf-8')))
        except OSError:
            pass
    return generated


ADMIN_TOKEN = _load_admin_token()

# Abilita background refresh (stale-while-revalidate)
BACKGROUND_REFRESH_ENABLED = True
