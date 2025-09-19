
import requests

from utils.logger_utils import setup_logger

from .engine import CloudflareBypasser

logger = setup_logger(__name__)


class CloudflareBypasser(CloudflareBypasser):
    """Bypass Cloudflare challenges using SeleniumBase + headless browser."""

    def __init__(self, driver: str = "chrome", headless: bool = True, wait_time: int = 10):
        pass

    def get_bypassed_page(self, url: str) -> str | None:
        response_html = internal_engine.get(url, retry=MAX_RETRY)
        logger.debug(f"Internal Bypasser response length: {len(response_html)}")

        if response_html and response_html.strip():
            return response_html
        raise requests.exceptions.RequestException("Failed to bypass Cloudflare with internal engine")

