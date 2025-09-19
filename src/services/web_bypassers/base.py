from abc import ABC, abstractmethod


class WebBypasser(ABC):
    """Abstract base for general (mostly Cloudflare) bypass implementations."""

    @abstractmethod
    def get_bypassed_page(self, url: str) -> str | None:
        """Fetch HTML from a URL, bypassing any restrictions if necessary."""
        ...
