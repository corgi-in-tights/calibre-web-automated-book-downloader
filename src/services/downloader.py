"""Network operations manager for the book downloader application."""

import src.services.network as network
import time
from io import BytesIO
from threading import Event
from typing import Callable, Optional
from urllib.parse import urlparse

import requests
from tqdm import tqdm

from utils.logger_utils import get_logger

network.init()

if USE_CF_BYPASS:
    if USING_EXTERNAL_BYPASSER:
        from cloudflare_bypasser_external import get_bypassed_page
    else:
        from web_bypassers import get_bypassed_page

logger = get_logger(__name__)

active_downloads = []


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

        logger.info("Book %s download %s", book_id, 'successful' if download_path else 'failed')

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


def html_get_page(url: str, retry: int = MAX_RETRY, use_bypasser: bool = False) -> str:
    """Fetch HTML content from a URL with retry mechanism.

    Args:
        url: Target URL
        retry: Number of retry attempts
        skip_404: Whether to skip 404 errors

    Returns:
        str: HTML content if successful, None otherwise
    """
    response = None
    try:
        logger.debug(f"html_get_page: {url}, retry: {retry}, use_bypasser: {use_bypasser}")
        if use_bypasser and USE_CF_BYPASS:
            logger.info(f"GET Using Cloudflare Bypasser for: {url}")
            return get_bypassed_page(url)
        else:
            logger.info(f"GET: {url}")
            response = requests.get(url, proxies=PROXIES)
            response.raise_for_status()
            logger.debug(f"Success getting: {url}")
            time.sleep(1)
        return str(response.text)

    except Exception as e:
        if retry == 0:
            logger.error_trace(f"Failed to fetch page: {url}, error: {e}")
            return ""

        if use_bypasser and USE_CF_BYPASS:
            logger.warning(f"Exception while using cloudflare bypass for URL: {url}")
            logger.warning(f"Exception: {e}")
            logger.warning(f"Response: {response}")
        elif response is not None and response.status_code == 404:
            logger.warning(f"404 error for URL: {url}")
            return ""
        elif response is not None and response.status_code == 403:
            logger.warning(f"403 detected for URL: {url}. Should retry using cloudflare bypass.")
            return html_get_page(url, retry - 1, True)

        sleep_time = DEFAULT_SLEEP * (MAX_RETRY - retry + 1)
        logger.warning(f"Retrying GET {url} in {sleep_time} seconds due to error: {e}")
        time.sleep(sleep_time)
        return html_get_page(url, retry - 1, use_bypasser)


def download_url(
    link: str,
    size: str = "",
    progress_callback: Optional[Callable[[float], None]] = None,
    cancel_flag: Optional[Event] = None,
) -> Optional[BytesIO]:
    """Download content from URL into a BytesIO buffer.

    Args:
        link: URL to download from

    Returns:
        BytesIO: Buffer containing downloaded content if successful
    """
    try:
        logger.info(f"Downloading from: {link}")
        response = requests.get(link, stream=True, proxies=PROXIES)
        response.raise_for_status()

        total_size: float = 0.0
        try:
            # we assume size is in MB
            total_size = float(size.strip().replace(" ", "").replace(",", ".").upper()[:-2].strip()) * 1024 * 1024
        except:
            total_size = float(response.headers.get("content-length", 0))

        buffer = BytesIO()

        # Initialize the progress bar with your guess
        pbar = tqdm(total=total_size, unit="B", unit_scale=True, desc="Downloading")
        for chunk in response.iter_content(chunk_size=1000):
            buffer.write(chunk)
            pbar.update(len(chunk))
            if progress_callback is not None:
                progress_callback(pbar.n * 100.0 / total_size)
            if cancel_flag is not None and cancel_flag.is_set():
                logger.info(f"Download cancelled: {link}")
                return None

        pbar.close()
        if buffer.tell() * 0.1 < total_size * 0.9:
            # Check the content of the buffer if its HTML or binary
            if response.headers.get("content-type", "").startswith("text/html"):
                logger.warn(f"Failed to download content for {link}. Found HTML content instead.")
                return None
        return buffer
    except requests.exceptions.RequestException as e:
        logger.error_trace(f"Failed to download from {link}: {e}")
        return None


def get_absolute_url(base_url: str, url: str) -> str:
    """Get absolute URL from relative URL and base URL.

    Args:
        base_url: Base URL
        url: Relative URL
    """
    if url.strip() == "":
        return ""
    if url.strip("#") == "":
        return ""
    if url.startswith("http"):
        return url
    parsed_url = urlparse(url)
    parsed_base = urlparse(base_url)
    if parsed_url.netloc == "" or parsed_url.scheme == "":
        parsed_url = parsed_url._replace(netloc=parsed_base.netloc, scheme=parsed_base.scheme)
    return parsed_url.geturl()



def download_book(book_id: str, cancel_flag: Event) -> str | None:
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



