from threading import RLock
from typing import Any

from cachetools import TTLCache

from conf import settings
from models import BookInfo, QueueStatus, SearchFilters, book_queue
from services.archive_managers import book_manager
from utils.logger_utils import get_logger
from utils.threading_utils import cached_lookup

from .archive_managers import ArchiveManager
from .registry import get_archive_managers, get_book_queue, get_or_create_service_registry

logger = get_logger(__name__)

def initialize_services():
    get_or_create_service_registry()


# ---- Archive Managers ----

def get_archive_manager_by_id(_id: str) -> ArchiveManager | None:
    return get_archive_managers().get(_id)

def get_archive_manager_by_any(archive: str | ArchiveManager | None) -> ArchiveManager:
    if isinstance(archive, ArchiveManager):
        return archive
    if isinstance(archive, str):
        return get_archive_manager_by_id(archive)
    return get_archive_manager_by_id(settings.DEFAULT_ARCHIVE_MANAGER)

# Hard-coded because I don't think it matters too much but could be made configurable later using registry.py
_search_cache = TTLCache(maxsize=5, ttl=86400) # 24 hours
_search_lock = RLock()

def search_books(
    query: str,
    filters: SearchFilters,
    archive: str | ArchiveManager | None = None,
) -> list[dict[str, Any]]:
    manager = get_archive_manager_by_any(archive)
    if manager is None:
        logger.error("No valid archive manager found for value: %s", archive)
        return []

    key = (query, str(filters), manager.identifier)
    return cached_lookup(
        _search_cache, _search_lock, key,
        lambda: manager.search_books(query, filters),
    )


_details_cache = TTLCache(maxsize=5, ttl=3600) # 1 hour
_details_lock = RLock()

def get_book_details(book_id: str, archive: str | ArchiveManager | None = None) -> dict[str, Any] | None:
    manager = get_archive_manager_by_any(archive)
    if manager is None:
        logger.error("No valid archive manager found for value: %s", archive)

    key = (book_id, manager.identifier)
    return cached_lookup(
        _details_cache, _details_lock, key,
        lambda: manager.get_book_details(book_id),
    )


# ---- Book Queue ----

def queue_book(book_id: str, archive: str | ArchiveManager | None = None, priority: int = 0) -> bool:
    manager = get_archive_manager_by_any(archive)
    if manager is None:
        logger.error("No valid archive manager found for value: %s", archive)
        return False
    return get_book_queue().add_book(book_id, archive, priority)


def update_download_progress(book_id: str, progress: float) -> None:
    """Update download progress."""
    get_book_queue().update_progress(book_id, progress)


def cancel_download(book_id: str) -> bool:
    """Cancel a download.

    Args:
        book_id: Book identifier to cancel

    Returns:
        bool: True if cancellation was successful
    """
    return get_book_queue().cancel_download(book_id)


def set_book_priority(book_id: str, priority: int) -> bool:
    """Set priority for a queued book.

    Args:
        book_id: Book identifier
        priority: New priority level (lower = higher priority)

    Returns:
        bool: True if priority was successfully changed
    """
    return get_book_queue().set_priority(book_id, priority)


def reorder_queue(book_priorities: dict[str, int]) -> bool:
    """Bulk reorder queue.

    Args:
        book_priorities: Dict mapping book_id to new priority

    Returns:
        bool: True if reordering was successful
    """
    return get_book_queue().reorder_queue(book_priorities)


def get_queue_display() -> list[dict[str, any]]:
    """Get current queue order for display."""
    return get_book_queue().get_queue_order()

def get_result_display() -> dict[str, any]:
    """Get current result store for display."""
    return []
