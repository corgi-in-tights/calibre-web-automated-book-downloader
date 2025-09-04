"""Data structures and models used across the application."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
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
    preview: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    year: Optional[str] = None
    language: Optional[str] = None
    format: Optional[str] = None
    size: Optional[str] = None
    info: Optional[Dict[str, List[str]]] = None
    download_urls: List[str] = field(default_factory=list)
    download_path: Optional[str] = None
    priority: int = 0
    progress: Optional[float] = None


@dataclass
class SearchFilters:
    isbn: Optional[List[str]] = None
    authors: Optional[List[str]] = None
    title: Optional[List[str]] = None
    lang: Optional[List[str]] = None
    sort: Optional[str] = None
    content: Optional[List[str]] = None
    format: Optional[List[str]] = None