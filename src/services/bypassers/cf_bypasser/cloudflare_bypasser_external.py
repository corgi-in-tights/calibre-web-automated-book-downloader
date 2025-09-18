
import requests
from src.config.logging import setup_logger

try:
    from config.settings import (
        ENABLE_LOGGING,
        EXT_BYPASSER_PATH,
        EXT_BYPASSER_TIMEOUT,
        EXT_BYPASSER_URL,
        LOG_FILE,
        LOG_LEVEL,
    )
except ImportError:
    raise RuntimeError("Failed to import environment variables. Are you using an `extbp` image?")

logger = setup_logger(__name__, LOG_FILE, LOG_LEVEL, ENABLE_LOGGING)


def get_bypassed_page(url: str) -> str | None:
    """Fetch HTML content from a URL using an External Cloudflare Resolver.

    Args:
        url: Target URL
    Returns:
        str: HTML content if successful, None otherwise
    """
    if not EXT_BYPASSER_URL or not EXT_BYPASSER_PATH:
        logger.error("Wrong External Bypass configuration. Please check your environment configuration.")
        return None
    ext_url = f"{EXT_BYPASSER_URL}{EXT_BYPASSER_PATH}"
    headers = {"Content-Type": "application/json"}
    data = {
        "cmd": "request.get",
        "url": url,
        "maxTimeout": EXT_BYPASSER_TIMEOUT,
    }
    response = requests.post(ext_url, headers=headers, json=data)
    response.raise_for_status()
    logger.debug(f"External Bypass response for '{url}': {response.json()['status']} - {response.json()['message']}")
    return response.json()["solution"]["response"]
