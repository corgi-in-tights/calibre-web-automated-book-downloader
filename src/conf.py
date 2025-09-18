import os
import threading
from types import ModuleType
from typing import Any

from utils.import_utils import load_module_by_name

_settings: ModuleType | None = None
_lock = threading.RLock()

def get_settings_path() -> str:
    """Return the current settings module path."""
    return os.getenv("CWA_BD_SETTINGS_MODULE", "config.settings")

def load_settings(temp_settings_path: str | None = None) -> None:
    global _settings  # noqa: PLW0603
    path = temp_settings_path or get_settings_path()
    _settings = load_module_by_name(path)
    return _settings

def get_settings():
    """Load settings once, cache result, and return the Settings instance."""
    if _settings is None:
        with _lock:
            if _settings is None:
                load_settings()
    return _settings


class _LazySettingsProxy:
    """Proxy object to access settings attributes lazily."""

    def __getattr__(self, name: str) -> Any:
        return getattr(get_settings(), name)

    def __dir__(self):
        return dir(get_settings())

# attribute accesss for convenience
settings = _LazySettingsProxy()

__all__ = ["get_settings", "settings"]
