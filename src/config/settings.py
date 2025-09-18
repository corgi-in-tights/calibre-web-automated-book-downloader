"""
Django-style settings for the Calibre Web Automated Book Downloader application.

This module consolidates all configuration settings from environment variables
and provides computed settings for the application.
"""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

def _string_to_bool(s: str) -> bool:
    """Convert string to boolean value."""
    return s.lower().strip() in ["true", "yes", "1", "y"]

def get_env(key: str, default: str = "") -> str:
    """Get environment variable or return default."""
    return os.getenv(key, default).strip()

def get_env_required(key: str, additional_error_msg: str | None = None) -> str:
    """Get environment variable or raise error if not found."""
    value = os.getenv(key).strip()
    if not value:
        msg = f"Missing required environment variable: {key}"
        if additional_error_msg is not None:
            msg += f" \n{additional_error_msg}"
        logger.error(msg)
        raise ValueError(msg)
    return value

# ==============================================================================
# APP SETTINGS
# ==============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.urandom(64) if "CWA_BD_SECRET_KEY" in os.environ else get_env_required("CWA_BD_SECRET_KEY")

BUILD_VERSION = get_env("BUILD_VERSION", "N/A")

RELEASE_VERSION = get_env("RELEASE_VERSION", "N/A")

APP_ENV = get_env("APP_ENV", "N/A").lower()

DEBUG = _string_to_bool(get_env("DEBUG", "false"))

FLASK_HOST = get_env("FLASK_HOST", "127.0.0.1")

FLASK_PORT = int(get_env("FLASK_PORT", "8084"))


# ==============================================================================
# LOGGING CONFIGURATION
# ==============================================================================

ENABLE_FILE_LOGGING = _string_to_bool(get_env("ENABLE_FILE_LOGGING", "true"))

if ENABLE_FILE_LOGGING:
    LOG_DIR = Path(get_env("LOG_ROOT", "/var/log/cwa-book-downloader"))
    LOG_FILE = LOG_DIR / "cwa-book-downloader.log"

LOG_LEVEL = "DEBUG" if DEBUG else get_env("LOG_LEVEL", "INFO").upper()


# ===============================================================================
# DEBUG CONFIGURATION
# ===============================================================================

DEBUG_LOG_KEYS = []  # Whitelist keys manually, TBD


# ==============================================================================
# DIRECTORY SETTINGS
# ==============================================================================

TMP_DIR = Path(get_env("TMP_DIR", "/tmp/cwa-book-downloader")) # noqa: S108

INGEST_DIR = Path(get_env("INGEST_DIR", "/cwa-book-ingest"))

# Create necessary directories
if ENABLE_FILE_LOGGING:
    LOG_DIR.mkdir(exist_ok=True)
TMP_DIR.mkdir(exist_ok=True)
INGEST_DIR.mkdir(exist_ok=True)


def is_cross_fs(path1: Path, path2: Path) -> bool:
    return path1.stat().st_dev != path2.stat().st_dev

CROSS_FILE_SYSTEM = is_cross_fs(TMP_DIR, INGEST_DIR)


# ==============================================================================
# AUTHENTICATION SETTINGS
# ==============================================================================

BASIC_AUTH_ENABLED = _string_to_bool(get_env("BASIC_AUTH_ENABLED", "true"))

_CWA_DB = os.get_env_required("CWA_DB_PATH")

CWA_DB_PATH = Path(_CWA_DB) if _CWA_DB else None


# ==============================================================================
# BOOK PROCESSING SETTINGS
# ==============================================================================

# Load supported languages from JSON
with (BASE_DIR / "data" / "book-languages.json").open() as file:
    _SUPPORTED_BOOK_LANGUAGES = json.load(file)

SUPPORTED_LANGUAGE_CODES = {entry["code"].lower() for entry in _SUPPORTED_BOOK_LANGUAGES}

# Supported file formats
SUPPORTED_FILE_FORMATS = get_env(
    "SUPPORTED_FILE_FORMATS", "epub,mobi,azw3,fb2,djvu,cbz,cbr",
).lower().split(",")

# Book language settings
raw_book_languages = get_env("BOOK_LANGUAGE", "en").lower().split(",")

BOOK_LANGUAGES = [lang.strip() for lang in raw_book_languages if lang.strip() in SUPPORTED_LANGUAGE_CODES]

DEFAULT_BOOK_LANGUAGE = BOOK_LANGUAGES[0] if BOOK_LANGUAGES else "en"

# Whether to use book title as filename when saving
USE_BOOK_TITLE = _string_to_bool(get_env("USE_BOOK_TITLE", "false"))

PRIORITIZE_WELIB = _string_to_bool(get_env("PRIORITIZE_WELIB", "false"))


# ==============================================================================
# DOWNLOAD SETTINGS
# ==============================================================================

MAX_RETRY = int(get_env("MAX_RETRY", "10"))

DEFAULT_SLEEP = int(get_env("DEFAULT_SLEEP", "5"))

MAIN_LOOP_SLEEP_TIME = int(get_env("MAIN_LOOP_SLEEP_TIME", "5"))

MAX_CONCURRENT_DOWNLOADS = int(get_env("MAX_CONCURRENT_DOWNLOADS", "3"))

DOWNLOAD_PROGRESS_UPDATE_INTERVAL = int(get_env("DOWNLOAD_PROGRESS_UPDATE_INTERVAL", "5"))

STATUS_TIMEOUT = int(get_env("STATUS_TIMEOUT", "3600"))


# ==============================================================================
# ANNA'S ARCHIVE SETTINGS
# ==============================================================================

AA_DONATOR_KEY = get_env("AA_DONATOR_KEY", "")

AA_BASE_URL = get_env("AA_BASE_URL", "auto")

AA_ADDITIONAL_URLS = get_env("AA_ADDITIONAL_URLS", "")

# Available Anna's Archive URLs
AA_AVAILABLE_URLS = ["https://annas-archive.org", "https://annas-archive.se", "https://annas-archive.li"]
if AA_ADDITIONAL_URLS:
    AA_AVAILABLE_URLS.extend([url.strip() for url in AA_ADDITIONAL_URLS.split(",") if url.strip()])


# ==============================================================================
# CLOUDFLARE BYPASS SETTINGS
# ==============================================================================

USE_CF_BYPASS = _string_to_bool(get_env("USE_CF_BYPASS", "true"))

BYPASS_RELEASE_INACTIVE_MIN = int(get_env("BYPASS_RELEASE_INACTIVE_MIN", "5"))

# External bypasser settings
USING_EXTERNAL_BYPASSER = _string_to_bool(get_env("USING_EXTERNAL_BYPASSER", "false"))

if USING_EXTERNAL_BYPASSER:
    EXT_BYPASSER_URL = get_env_required(
        "EXT_BYPASSER_URL",
        additional_error_msg="If using an external bypasser, set EXT_BYPASSER_URL to the full URL, e.g. http://bypasser:5000",
    )
    EXT_BYPASSER_TIMEOUT = int(get_env("EXT_BYPASSER_TIMEOUT", "60000"))

# Virtual display settings for internal cloudflare bypasser
if not USING_EXTERNAL_BYPASSER:
    VIRTUAL_SCREEN_SIZE = (1024, 768)
    RECORDING_DIR = LOG_DIR / "recording"
    if DEBUG:
        RECORDING_DIR.mkdir(parents=True, exist_ok=True)

# ==============================================================================
# NETWORK SETTINGS
# ==============================================================================

# Proxy settings
HTTP_PROXY = get_env("HTTP_PROXY", "")
HTTPS_PROXY = get_env("HTTPS_PROXY", "")
PROXIES = {}
if HTTP_PROXY:
    PROXIES["http"] = HTTP_PROXY
if HTTPS_PROXY:
    PROXIES["https"] = HTTPS_PROXY

# Tor settings
USING_TOR = _string_to_bool(get_env("USING_TOR", "false"))

# DNS settings
_CUSTOM_DNS = get_env("CUSTOM_DNS", "")
USE_DOH = _string_to_bool(get_env("USE_DOH", "false"))

# If using Tor, disable custom DNS, DOH, and proxy
if USING_TOR:
    _CUSTOM_DNS = ""
    USE_DOH = False
    HTTP_PROXY = ""
    HTTPS_PROXY = ""
    PROXIES = {}

# DNS resolution settings
CUSTOM_DNS = []
DOH_SERVER = ""

if _CUSTOM_DNS:
    _custom_dns = _CUSTOM_DNS.lower().strip()

    if _custom_dns == "google":
        CUSTOM_DNS = [
            "8.8.8.8",
            "8.8.4.4",
            "2001:4860:4860:0000:0000:0000:0000:8888",
            "2001:4860:4860:0000:0000:0000:0000:8844",
        ]
        DOH_SERVER = "https://dns.google/dns-query"
    elif _custom_dns == "quad9":
        CUSTOM_DNS = [
            "9.9.9.9",
            "149.112.112.112",
            "2620:00fe:0000:0000:0000:0000:0000:00fe",
            "2620:00fe:0000:0000:0000:0000:0000:0009",
        ]
        DOH_SERVER = "https://dns.quad9.net/dns-query"
    elif _custom_dns == "cloudflare":
        CUSTOM_DNS = [
            "1.1.1.1",
            "1.0.0.1",
            "2606:4700:4700:0000:0000:0000:0000:1111",
            "2606:4700:4700:0000:0000:0000:0000:1001",
        ]
        DOH_SERVER = "https://cloudflare-dns.com/dns-query"
    elif _custom_dns == "opendns":
        CUSTOM_DNS = [
            "208.67.222.222",
            "208.67.220.220",
            "2620:0119:0035:0000:0000:0000:0000:0035",
            "2620:0119:0053:0000:0000:0000:0000:0053",
        ]
        DOH_SERVER = "https://doh.opendns.com/dns-query"
    else:
        # Custom DNS IPs
        _custom_dns_ips = _custom_dns.split(",")
        CUSTOM_DNS = [
            dns.strip() for dns in _custom_dns_ips if dns.replace(":", "").replace(".", "").strip().isdigit()
        ]

# Apply DOH settings
if not USE_DOH:
    DOH_SERVER = ""

# ==============================================================================
# CUSTOM SCRIPT SETTINGS
# ==============================================================================

CUSTOM_SCRIPT = get_env("CUSTOM_SCRIPT", "")
# Validate custom script
if CUSTOM_SCRIPT:
    if not Path(CUSTOM_SCRIPT).exists():
        logger.warning("CUSTOM_SCRIPT %s does not exist", CUSTOM_SCRIPT)
        CUSTOM_SCRIPT = ""
    elif not os.access(CUSTOM_SCRIPT, os.X_OK):
        logger.warning("CUSTOM_SCRIPT %s is not executable", CUSTOM_SCRIPT)
        CUSTOM_SCRIPT = ""
