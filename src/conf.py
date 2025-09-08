import os
from typing import Optional
from threading import RLock
from config.settings import Settings

"""
Exists to manage lazy loading of settings configuration. Designed to be able to support thread-safe dynamic reloading, different settings environments, etc.
Personally not a big fan of importing directly from settings.py, conf should be loaded only when the app lifecycle calls for it/provided by environment.
"""

_settings: Optional[Settings] = None
_lock = RLock()

def get_settings_path() -> str:
    return os.getenv("SETTINGS_PATH", "config/settings.py")

def load_settings(settings_path: Optional[str] = None) -> Settings:
    return Settings(settings_path or get_settings_path())

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        with _lock:
            if _settings is None:
                _settings = load_settings()
    return _settings

def set_settings(settings_instance: Settings) -> None:
    global _settings
    with _lock:
        _settings = settings_instance

def reload_settings(settings_path: Optional[str] = None) -> Settings:
    """Force re-read from disk/env (e.g., SIGHUP handler or admin endpoint)."""
    new_settings = load_settings(settings_path)
    set_settings(new_settings)
    return new_settings

# Django-like attribute access *without* eager import
class _LazySettings:
    def __getattr__(self, name: str):
        return getattr(get_settings(), name)

settings = _LazySettings()


__all__ = ['settings', 'get_settings', 'set_settings']
