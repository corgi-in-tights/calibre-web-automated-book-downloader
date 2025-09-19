
from threading import RLock
from typing import Any

from conf import settings
from utils.logger_utils import get_logger

from .archive_managers import ArchiveManager, initialize_archive_manager
from .book_queue import BookQueue
from .web_bypassers import WebBypasser, initialize_web_bypasser

logger = get_logger(__name__)

# Singleton containing all the runtime services (i.e. anything that should be initialized only once on command)
class ServiceRegistry:
    archive_managers: dict[str, ArchiveManager]
    web_bypassers: dict[str, WebBypasser]
    queue: BookQueue
    results: dict[str, Any]

registry: ServiceRegistry | None = None
_lock = RLock()


def _initialize_service_registry() -> ServiceRegistry:
    registry = ServiceRegistry()

    registry.archive_managers = {
        _id: initialize_archive_manager(config)
        for _id, config in settings.ARCHIVE_MANAGERS.items()
    }
    registry.web_bypassers = {
        _id: initialize_web_bypasser(config)
        for _id, config in settings.WEB_BYPASSERS.items()
    }
    registry.queue = BookQueue()
    registry.result_store = {}
    return registry


def get_or_create_service_registry() -> ServiceRegistry:
    global registry  # noqa: PLW0603
    if registry is None:
        logger.info("Initializing runtime services...")
        with _lock:
            if registry is not None:  # Just to be sure :)
                registry = _initialize_service_registry()
        logger.info("Runtime services initialized successfully.")
    return registry


# 'Malicious' function to raise if services are not initialized, initialization should be expected behaviour.
def _raise_if_uninitialized():
    if registry is None:
        msg = "Service registry not initialized, call registry.get_or_create_service_registry() first."
        logger.error(msg)
        raise ValueError(msg)

def get_web_bypassers() -> dict[str, WebBypasser]:
    _raise_if_uninitialized()
    return registry.web_bypassers

def get_archive_managers() -> dict[str, ArchiveManager]:
    _raise_if_uninitialized()
    return registry.archive_managers

def get_book_queue() -> BookQueue:
    _raise_if_uninitialized()
    return registry.queue

def get_result_store() -> dict[str, Any]:
    _raise_if_uninitialized()
    return registry.result_store
