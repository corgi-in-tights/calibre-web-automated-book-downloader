import requests

from utils.logger_utils import get_logger

from .base import WebBypasser


class ExternalWebBypasser(WebBypasser):
    """Abstract base for general (mostly Cloudflare) bypass implementations."""

    def __init__(self, ext_bypasser_url: str, ext_bypasser_path: str, ext_bypasser_timeout: int):
        self.ext_bypasser_url = ext_bypasser_url
        self.ext_bypasser_path = ext_bypasser_path
        self.ext_bypasser_timeout = ext_bypasser_timeout
        self.logger = get_logger(__name__)

    def get_bypassed_page(self, url: str) -> str | None:
        """Fetch HTML from a URL, bypassing any restrictions if necessary."""
        if not self.ext_bypasser_url or not self.ext_bypasser_path:
            self.logger.error("Wrong External Bypass configuration. Please check your environment configuration.")
            return None
        ext_url = f"{self.ext_bypasser_url}{self.ext_bypasser_path}"
        headers = {"Content-Type": "application/json"}
        data = {
            "cmd": "request.get",
            "url": url,
            "maxTimeout": self.ext_bypasser_timeout,
        }
        response = requests.post(ext_url, headers=headers, json=data, timeout=20)
        response.raise_for_status()
        self.logger.debug(
            "External Bypass response for '%s': %s - %s", url, response.json()["status"], response.json()["message"],
        )
        return response.json()["solution"]["response"]
