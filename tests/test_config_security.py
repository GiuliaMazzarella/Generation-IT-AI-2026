import importlib
import sys


def _reload_config(monkeypatch, **env_vars):
    for key in ('WEATHER_ADMIN_TOKEN', 'WEATHER_ENCRYPTION_KEY', 'WEATHER_ENABLE_PERSISTENT_CACHE'):
        monkeypatch.delenv(key, raising=False)
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    sys.modules.pop('config', None)
    import config
    return importlib.reload(config)


def test_admin_token_prefers_environment_variable(monkeypatch):
    cfg = _reload_config(monkeypatch, WEATHER_ADMIN_TOKEN='env-secret-token')
    assert cfg.ADMIN_TOKEN == 'env-secret-token'


def test_persistent_cache_disabled_by_default(monkeypatch):
    cfg = _reload_config(monkeypatch)
    assert cfg.PERSISTENT_CACHE_ENABLED is False
