"""Data structures and models used across the application."""

from dataclasses import dataclass, field
from enum import Enum


class QueueStatus(str, Enum):
    """Enum for possible book queue statuses."""
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    AVAILABLE = "available"
    ERROR = "error"
    DONE = "done"
    CANCELLED = "cancelled"

@dataclass
class QueueItem:
    """Queue item with priority and metadata."""
    book_id: str
    priority: int
    added_time: float

    def __lt__(self, other):
        """Compare items for priority queue (lower priority number = higher precedence)."""
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.added_time < other.added_time

@dataclass
class BookInfo:
    """Data class representing book information."""
    id: str
    title: str
    preview: str | None = None
    author: str | None = None
    publisher: str | None = None
    year: str | None = None
    language: str | None = None
    format: str | None = None
    size: str | None = None
    info: dict[str, list[str]] | None = None
    download_urls: list[str] = field(default_factory=list)
    download_path: str | None = None
    priority: int = 0
    progress: float | None = None


@dataclass
class SearchFilters:
    isbn: list[str] | None = None
    authors: list[str] | None = None
    title: list[str] | None = None
    lang: list[str] | None = None
    sort: str | None = None
    content: list[str] | None = None
    format: list[str] | None = None
