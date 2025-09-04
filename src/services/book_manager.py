"""Book download manager handling search and retrieval operations."""

import time, json, re
from pathlib import Path
from urllib.parse import quote
from typing import List, Optional, Dict, Union, Callable
from threading import Event
from bs4 import BeautifulSoup, Tag, NavigableString, ResultSet

import .downloader as downloader
from .logger import setup_logger
from config.settings import (
    SUPPORTED_FORMATS, BOOK_LANGUAGE, AA_BASE_URL, AA_DONATOR_KEY, 
    USE_CF_BYPASS, PRIORITIZE_WELIB, LOG_FILE, LOG_LEVEL, ENABLE_LOGGING
)
from src.services.models import BookInfo, SearchFilters

logger = setup_logger(__name__, LOG_FILE, LOG_LEVEL, ENABLE_LOGGING)


class BookManager:
    def __init__(self):
        pass
    
    def build_query_url(self, query: str, filters: SearchFilters) -> str:
        """Construct search URL based on query and filters.

        Args:
            query: Search term (ISBN, title, author, etc.)
            filters: SearchFilters object with filter settings
        """
        query_html = quote(query)

        if filters.isbn:
            # ISBNs are included in query string
            isbns = " || ".join(
                [f"('isbn13:{isbn}' || 'isbn10:{isbn}')" for isbn in filters.isbn]
            )
            query_html = quote(f"({isbns}) {query}")

        if filters.authors:
            authors = " || ".join([f"author:{author}" for author in filters.authors])
            query_html = quote(f"({authors}) {query}")

        filters_query = ""

        for value in filters.lang or BOOK_LANGUAGE:
            if value != "all":
                filters_query += f"&lang={quote(value)}"

        if filters.sort:
            filters_query += f"&sort={quote(filters.sort)}"

        if filters.content:
            for value in filters.content:
                filters_query += f"&content={quote(value)}"

        # Handle format filter
        formats_to_use = filters.format if filters.format else SUPPORTED_FORMATS

        index = 1
        for filter_type, filter_values in vars(filters).items():
            if filter_type == "author" or filter_type == "title" and filter_values:
                for value in filter_values:
                    filters_query += (
                        f"&termtype_{index}={filter_type}&termval_{index}={quote(value)}"
                    )
                    index += 1

        return (
            f"{AA_BASE_URL}"
            f"/search?index=&page=1&display=table"
            f"&acc=aa_download&acc=external_download"
            f"&ext={'&ext='.join(formats_to_use)}"
            f"&q={query_html}"
            f"{filters_query}"
        )


    def search_books_by_url(self, url: str) -> List[BookInfo]:
        """Fetch books from a specific URL.

        Args:
            url: Search URL to fetch results from

        Returns:
            List[BookInfo]: List of matching books

        Raises:
            Exception: If no books found or parsing fails
        """
        html = downloader.html_get_page(url)
        if not html:
            raise Exception("Failed to fetch search results")

        if "No files found." in html:
            logger.info(f"No books found for url: {url}")
            raise Exception("No books found. Please try another query.")

        soup = BeautifulSoup(html, "html.parser")
        tbody: Tag | NavigableString | None = soup.find("table")

        if not tbody:
            logger.warning(f"No results table found for url: {url}")
            raise Exception("No books found. Please try another query.")

        books = []
        if isinstance(tbody, Tag):
            for line_tr in tbody.find_all("tr"):
                try:
                    book = _parse_search_result_row(line_tr)
                    if book:
                        books.append(book)
                except Exception as e:
                    logger.error_trace(f"Failed to parse search result row: {e}")

        books.sort(
            key=lambda x: (
                SUPPORTED_FORMATS.index(x.format)
                if x.format in SUPPORTED_FORMATS
                else len(SUPPORTED_FORMATS)
            )
        )

        return books
    
    
    def get_books_by_query(self, query: str, filters: SearchFilters) -> List[BookInfo]:
        """Search for books matching the query.

        Args:
            query: Search term (ISBN, title, author, etc.)
            filters: SearchFilters object with filter settings

        Returns:
            List[BookInfo]: List of matching books

        Raises:
            Exception: If no books found or parsing fails
        """
        url = self.build_query_url(query, filters)
        return self.search_books_by_url(url)
        
        
    def get_book_info(book_id: str) -> BookInfo:
        """Get detailed information for a specific book.

        Args:
            book_id: Book identifier (MD5 hash)

        Returns:
            BookInfo: Detailed book information
        """
        url = f"{AA_BASE_URL}/md5/{book_id}"
        html = downloader.html_get_page(url)

        if not html:
            raise Exception(f"Failed to fetch book info for ID: {book_id}")

        soup = BeautifulSoup(html, "html.parser")

        return _parse_book_info_page(soup, book_id)







def _get_download_urls_from_welib(book_id: str) -> set[str]:
    """Get download urls from welib.org."""
    url = f"https://welib.org/md5/{book_id}"
    logger.info(f"Getting download urls from welib.org for {book_id}. While this uses the bypasser, it will not start downloading them yet.")
    html = downloader.html_get_page(url, use_bypasser=True)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    download_links = soup.find_all("a", href=True)
    download_links = [link["href"] for link in download_links]
    download_links = [link for link in download_links if "/slow_download/" in link]
    download_links = [downloader.get_absolute_url(url, link) for link in download_links]
    return set(download_links)

def _extract_book_metadata(
    metadata_divs
) -> Dict[str, List[str]]:
    """Extract metadata from book info divs."""
    info: Dict[str, List[str]] = {}

    # Process the first set of metadata
    sub_datas = metadata_divs.find_all("div")[0]
    sub_datas = list(sub_datas.children)
    for sub_data in sub_datas:
        if sub_data.text.strip() == "":
            continue
        sub_data = list(sub_data.children)
        key = sub_data[0].text.strip()
        value = sub_data[1].text.strip()
        if key not in info:
            info[key] = set()
        info[key].add(value)
    
    # make set into list
    for key, value in info.items():
        info[key] = list(value)

    # Filter relevant metadata
    relevant_prefixes = [
        "ISBN-",
        "ALTERNATIVE",
        "ASIN",
        "Goodreads",
        "Language",
        "Year",
    ]
    return {
        k.strip(): v
        for k, v in info.items()
        if any(k.lower().startswith(prefix.lower()) for prefix in relevant_prefixes)
        and "filename" not in k.lower()
    }


def download_book(book_info: BookInfo, book_path: Path, progress_callback: Optional[Callable[[float], None]] = None, cancel_flag: Optional[Event] = None) -> bool:
    """Download a book from available sources.

    Args:
        book_id: Book identifier (MD5 hash)
        title: Book title for logging

    Returns:
        Optional[BytesIO]: Book content buffer if successful
    """

    if len(book_info.download_urls) == 0:
        book_info = get_book_info(book_info.id)
    download_links = book_info.download_urls

    # If AA_DONATOR_KEY is set, use the fast download URL. Else try other sources.
    if AA_DONATOR_KEY != "":
        download_links.insert(
            0,
            f"{AA_BASE_URL}/dyn/api/fast_download.json?md5={book_info.id}&key={AA_DONATOR_KEY}",
        )

    for link in download_links:
        try:
            download_url = _get_download_url(link, book_info.title, cancel_flag)
            if download_url != "":
                logger.info(f"Downloading `{book_info.title}` from `{download_url}`")

                data = downloader.download_url(download_url, book_info.size or "", progress_callback, cancel_flag)
                if not data:
                    raise Exception("No data received")

                logger.info(f"Download finished. Writing to {book_path}")
                with open(book_path, "wb") as f:
                    f.write(data.getbuffer())
                logger.info(f"Writing `{book_info.title}` successfully")
                return True

        except Exception as e:
            logger.error_trace(f"Failed to download from {link}: {e}")
            continue

    return False


def _get_download_url(link: str, title: str, cancel_flag: Optional[Event] = None) -> str:
    """Extract actual download URL from various source pages."""

    url = ""

    if link.startswith(f"{AA_BASE_URL}/dyn/api/fast_download.json"):
        page = downloader.html_get_page(link)
        url = json.loads(page).get("download_url")
    else:
        html = downloader.html_get_page(link)

        if html == "":
            return ""

        soup = BeautifulSoup(html, "html.parser")

        if link.startswith("https://z-lib."):
            download_link = soup.find_all("a", href=True, class_="addDownloadedBook")
            if download_link:
                url = download_link[0]["href"]
        elif "/slow_download/" in link:
            download_links = soup.find_all("a", href=True, string="📚 Download now")
            if not download_links:
                countdown = soup.find_all("span", class_="js-partner-countdown")
                if countdown:
                    sleep_time = int(countdown[0].text)
                    logger.info(f"Waiting {sleep_time}s for {title}")
                    if cancel_flag is not None and cancel_flag.wait(timeout=sleep_time):
                        logger.info(f"Cancelled wait for {title}")
                        return ""
                    url = _get_download_url(link, title, cancel_flag)
            else:
                url = download_links[0]["href"]
        else:
            url = soup.find_all("a", string="GET")[0]["href"]

    return downloader.get_absolute_url(link, url)
