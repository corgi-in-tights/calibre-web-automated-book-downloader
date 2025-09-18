"""Backend logic for the book download application."""

import os
import shutil
import subprocess
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from threading import Event
from typing import Any

from conf import settings
from models import BookInfo, QueueStatus, SearchFilters, book_queue
from services.archive_managers import book_manager
from utils.book_utils import sanitize_filename
from utils.logger_utils import get_logger

from .archive_managers import ArchiveManager

logger = get_logger(__name__)


def search_books(query: str, filters: SearchFilters, archive: str | ArchiveManager) -> list[dict[str, Any]]:
    pass


def get_book_info(book_id: str) -> dict[str, Any] | None:
    pass


def queue_book(book_id: str, priority: int = 0) -> bool:
    pass


def get_queue():
    pass



def get_book_data(book_id: str) -> tuple[bytes | None, BookInfo]:
    """Get book data for a specific book, including its title.

    Args:
        book_id: Book identifier

    Returns:
        Tuple[Optional[bytes], str]: Book data if available, and the book title
    """
    try:
        book_info = book_queue._book_data[book_id]
        path = book_info.download_path
        with open(path, "rb") as f:
            return f.read(), book_info
    except Exception as e:
        logger.error_trace(f"Error getting book data: {e}")
        if book_info:
            book_info.download_path = None
        return None, book_info if book_info else BookInfo(id=book_id, title="Unknown")


def down(book_id: str, cancel_flag: Event) -> Optional[str]:
    """Download and process a book with cancellation support.

    Args:
        book_id: Book identifier
        cancel_flag: Threading event to signal cancellation

    Returns:
        str: Path to the downloaded book if successful, None otherwise
    """
    try:
        # Check for cancellation before starting
        if cancel_flag.is_set():
            logger.info(f"Download cancelled before starting: {book_id}")
            return None

        book_info = book_queue._book_data[book_id]
        logger.info(f"Starting download: {book_info.title}")

        if USE_BOOK_TITLE:
            book_name = _sanitize_filename(book_info.title)
        else:
            book_name = book_id
        book_name += f".{book_info.format}"
        book_path = TMP_DIR / book_name

        # Check cancellation before download
        if cancel_flag.is_set():
            logger.info(f"Download cancelled before book manager call: {book_id}")
            return None

        progress_callback = lambda progress: update_download_progress(book_id, progress)
        success = book_manager.download_book(book_info, book_path, progress_callback, cancel_flag)

        # Stop progress updates
        cancel_flag.wait(0.1)  # Brief pause for progress thread cleanup

        if cancel_flag.is_set():
            logger.info("Download cancelled during download: %s", book_id)
            # Clean up partial download
            if book_path.exists():
                book_path.unlink()
            return None

        if not success:
            raise Exception("Unknown error downloading book")

        # Check cancellation before post-processing
        if cancel_flag.is_set():
            logger.info(f"Download cancelled before post-processing: {book_id}")
            if book_path.exists():
                book_path.unlink()
            return None

        if CUSTOM_SCRIPT:
            logger.info(f"Running custom script: {CUSTOM_SCRIPT}")
            subprocess.run([CUSTOM_SCRIPT, book_path])

        intermediate_path = INGEST_DIR / f"{book_id}.crdownload"
        final_path = INGEST_DIR / book_name

        if os.path.exists(book_path):
            logger.info(f"Moving book to ingest directory: {book_path} -> {final_path}")
            try:
                shutil.move(book_path, intermediate_path)
            except Exception as e:
                try:
                    logger.debug(f"Error moving book: {e}, will try copying instead")
                    shutil.move(book_path, intermediate_path)
                except Exception as e:
                    logger.debug(f"Error copying book: {e}, will try copying without permissions instead")
                    shutil.copyfile(book_path, intermediate_path)
                os.remove(book_path)

            # Final cancellation check before completing
            if cancel_flag.is_set():
                logger.info(f"Download cancelled before final rename: {book_id}")
                if intermediate_path.exists():
                    intermediate_path.unlink()
                return None

            os.rename(intermediate_path, final_path)
            logger.info(f"Download completed successfully: {book_info.title}")

        return str(final_path)
    except Exception as e:
        if cancel_flag.is_set():
            logger.info(f"Download cancelled during error handling: {book_id}")
        else:
            logger.error_trace(f"Error downloading book: {e}")
        return None


def update_download_progress(book_id: str, progress: float) -> None:
    """Update download progress."""
    book_queue.update_progress(book_id, progress)


def cancel_download(book_id: str) -> bool:
    """Cancel a download.

    Args:
        book_id: Book identifier to cancel

    Returns:
        bool: True if cancellation was successful
    """
    return book_queue.cancel_download(book_id)


def set_book_priority(book_id: str, priority: int) -> bool:
    """Set priority for a queued book.

    Args:
        book_id: Book identifier
        priority: New priority level (lower = higher priority)

    Returns:
        bool: True if priority was successfully changed
    """
    return book_queue.set_priority(book_id, priority)


def reorder_queue(book_priorities: Dict[str, int]) -> bool:
    """Bulk reorder queue.

    Args:
        book_priorities: Dict mapping book_id to new priority

    Returns:
        bool: True if reordering was successful
    """
    return book_queue.reorder_queue(book_priorities)


def get_queue_order() -> List[Dict[str, any]]:
    """Get current queue order for display."""
    return book_queue.get_queue_order()


def get_active_downloads() -> List[str]:
    """Get list of currently active downloads."""
    return book_queue.get_active_downloads()


def clear_completed() -> int:
    """Clear all completed downloads from tracking."""
    return book_queue.clear_completed()


def _process_single_download(book_id: str, cancel_flag: Event) -> None:
    """Process a single download job."""
    try:
        book_queue.update_status(book_id, QueueStatus.DOWNLOADING)
        download_path = _download_book_with_cancellation(book_id, cancel_flag)

        if cancel_flag.is_set():
            book_queue.update_status(book_id, QueueStatus.CANCELLED)
            return

        if download_path:
            book_queue.update_download_path(book_id, download_path)
            new_status = QueueStatus.AVAILABLE
        else:
            new_status = QueueStatus.ERROR

        book_queue.update_status(book_id, new_status)

        logger.info(f"Book {book_id} download {'successful' if download_path else 'failed'}")

    except Exception as e:
        if not cancel_flag.is_set():
            logger.error_trace(f"Error in download processing: {e}")
            book_queue.update_status(book_id, QueueStatus.ERROR)
        else:
            logger.info(f"Download cancelled: {book_id}")
            book_queue.update_status(book_id, QueueStatus.CANCELLED)


def concurrent_download_loop() -> None:
    """Main download coordinator using ThreadPoolExecutor for concurrent downloads."""
    logger.info(f"Starting concurrent download loop with {MAX_CONCURRENT_DOWNLOADS} workers")

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_DOWNLOADS, thread_name_prefix="BookDownload") as executor:
        active_futures: Dict[Future, str] = {}  # Track active download futures

        while True:
            # Clean up completed futures
            completed_futures = [f for f in active_futures if f.done()]
            for future in completed_futures:
                book_id = active_futures.pop(future)
                try:
                    future.result()  # This will raise any exceptions from the worker
                except Exception as e:
                    logger.error_trace(f"Future exception for {book_id}: {e}")

            # Start new downloads if we have capacity
            while len(active_futures) < MAX_CONCURRENT_DOWNLOADS:
                next_download = book_queue.get_next()
                if not next_download:
                    break

                book_id, cancel_flag = next_download
                logger.info(f"Starting concurrent download: {book_id}")

                # Submit download job to thread pool
                future = executor.submit(_process_single_download, book_id, cancel_flag)
                active_futures[future] = book_id

            # Brief sleep to prevent busy waiting
            time.sleep(MAIN_LOOP_SLEEP_TIME)



def start_coordinator():
    download_coordinator_thread = threading.Thread(
        target=concurrent_download_loop, daemon=True, name="DownloadCoordinator",
    )
    download_coordinator_thread.start()

    logger.info("Download system initialized with %s concurrent workers", settings.MAX_CONCURRENT_DOWNLOADS)
