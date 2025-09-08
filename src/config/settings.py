"""
Django-style settings for the Calibre Web Automated Book Downloader application.

This module consolidates all configuration settings from environment variables
and provides computed settings for the application.
"""

import os
import json
from pathlib import Path

from src.logger import setup_logger



# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

def _string_to_bool(s: str) -> bool:
    """Convert string to boolean value."""
    return s.lower() in ["true", "yes", "1", "y"]


# ==============================================================================
# APP SETTINGS
# ==============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

BUILD_VERSION = os.getenv("BUILD_VERSION", "N/A")

RELEASE_VERSION = os.getenv("RELEASE_VERSION", "N/A")

APP_ENV = os.getenv("APP_ENV", "N/A").lower()

DEBUG = _string_to_bool(os.getenv("DEBUG", "false"))

DOCKERMODE = _string_to_bool(os.getenv("DOCKERMODE", "false"))

FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")

FLASK_PORT = int(os.getenv("FLASK_PORT", "8084"))


# ==============================================================================
# LOGGING CONFIGURATION
# ==============================================================================

ENABLE_LOGGING = _string_to_bool(os.getenv("ENABLE_LOGGING", "true"))

LOG_ROOT = Path(os.getenv("LOG_ROOT", "/var/log/"))

LOG_DIR = LOG_ROOT / "cwa-book-downloader"

# Set log level based on debug mode
LOG_LEVEL = "DEBUG" if DEBUG else os.getenv("LOG_LEVEL", "INFO").upper()

LOG_FILE = LOG_DIR / "cwa-book-downloader.log"

# ==============================================================================
# DIRECTORY SETTINGS
# ==============================================================================

TMP_DIR = Path(os.getenv("TMP_DIR", "/tmp/cwa-book-downloader"))

INGEST_DIR = Path(os.getenv("INGEST_DIR", "/cwa-book-ingest"))

# Create necessary directories
if ENABLE_LOGGING:
    LOG_DIR.mkdir(exist_ok=True)
TMP_DIR.mkdir(exist_ok=True)
INGEST_DIR.mkdir(exist_ok=True)

# Check if directories are on different file systems
CROSS_FILE_SYSTEM = os.stat(TMP_DIR).st_dev != os.stat(INGEST_DIR).st_dev


# ==============================================================================
# AUTHENTICATION SETTINGS
# ==============================================================================

# Use CWA's authentication database
_CWA_DB = os.getenv("CWA_DB_PATH")
CWA_DB_PATH = Path(_CWA_DB) if _CWA_DB else None


# ==============================================================================
# BOOK PROCESSING SETTINGS
# ==============================================================================

# Load supported book languages
with open(BASE_DIR / "data" / "book-languages.json") as file:
    _SUPPORTED_BOOK_LANGUAGES = json.load(file)

# Supported file formats
SUPPORTED_FORMATS = os.getenv("SUPPORTED_FORMATS", "epub,mobi,azw3,fb2,djvu,cbz,cbr").lower().split(",")

# Book language settings
_BOOK_LANGUAGE = os.getenv("BOOK_LANGUAGE", "en").lower()
BOOK_LANGUAGE = [lang.strip() for lang in _BOOK_LANGUAGE.split(',')]
BOOK_LANGUAGE = [lang for lang in BOOK_LANGUAGE if lang in [l['code'] for l in _SUPPORTED_BOOK_LANGUAGES]]
if not BOOK_LANGUAGE:
    BOOK_LANGUAGE = ['en']

# Book processing preferences
USE_BOOK_TITLE = _string_to_bool(os.getenv("USE_BOOK_TITLE", "false"))
PRIORITIZE_WELIB = _string_to_bool(os.getenv("PRIORITIZE_WELIB", "false"))

# ==============================================================================
# DOWNLOAD SETTINGS
# ==============================================================================

MAX_RETRY = int(os.getenv("MAX_RETRY", "10"))

DEFAULT_SLEEP = int(os.getenv("DEFAULT_SLEEP", "5"))

MAIN_LOOP_SLEEP_TIME = int(os.getenv("MAIN_LOOP_SLEEP_TIME", "5"))

MAX_CONCURRENT_DOWNLOADS = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "3"))

DOWNLOAD_PROGRESS_UPDATE_INTERVAL = int(os.getenv("DOWNLOAD_PROGRESS_UPDATE_INTERVAL", "5"))

STATUS_TIMEOUT = int(os.getenv("STATUS_TIMEOUT", "3600"))


# ==============================================================================
# ANNA'S ARCHIVE SETTINGS
# ==============================================================================

AA_DONATOR_KEY = os.getenv("AA_DONATOR_KEY", "").strip()

AA_BASE_URL = os.getenv("AA_BASE_URL", "auto").strip()

AA_ADDITIONAL_URLS = os.getenv("AA_ADDITIONAL_URLS", "").strip()

# Available Anna's Archive URLs
AA_AVAILABLE_URLS = [
    "https://annas-archive.org",
    "https://annas-archive.se", 
    "https://annas-archive.li"
]
if AA_ADDITIONAL_URLS:
    AA_AVAILABLE_URLS.extend([url.strip() for url in AA_ADDITIONAL_URLS.split(",") if url.strip()])


# ==============================================================================
# CLOUDFLARE BYPASS SETTINGS
# ==============================================================================

USE_CF_BYPASS = _string_to_bool(os.getenv("USE_CF_BYPASS", "true"))

BYPASS_RELEASE_INACTIVE_MIN = int(os.getenv("BYPASS_RELEASE_INACTIVE_MIN", "5"))

# External bypasser settings
USING_EXTERNAL_BYPASSER = _string_to_bool(os.getenv("USING_EXTERNAL_BYPASSER", "false"))

if USING_EXTERNAL_BYPASSER:
    EXT_BYPASSER_URL = os.getenv("EXT_BYPASSER_URL", "http://flaresolverr:8191").strip()
    EXT_BYPASSER_PATH = os.getenv("EXT_BYPASSER_PATH", "/v1").strip()
    EXT_BYPASSER_TIMEOUT = int(os.getenv("EXT_BYPASSER_TIMEOUT", "60000"))

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
HTTP_PROXY = os.getenv("HTTP_PROXY", "").strip()
HTTPS_PROXY = os.getenv("HTTPS_PROXY", "").strip()
PROXIES = {}
if HTTP_PROXY:
    PROXIES["http"] = HTTP_PROXY
if HTTPS_PROXY:
    PROXIES["https"] = HTTPS_PROXY

# Tor settings
USING_TOR = _string_to_bool(os.getenv("USING_TOR", "false"))

# DNS settings
_CUSTOM_DNS = os.getenv("CUSTOM_DNS", "").strip()
USE_DOH = _string_to_bool(os.getenv("USE_DOH", "false"))

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
            "8.8.8.8", "8.8.4.4", 
            "2001:4860:4860:0000:0000:0000:0000:8888", 
            "2001:4860:4860:0000:0000:0000:0000:8844"
        ]
        DOH_SERVER = "https://dns.google/dns-query"
    elif _custom_dns == "quad9":
        CUSTOM_DNS = [
            "9.9.9.9", "149.112.112.112",
            "2620:00fe:0000:0000:0000:0000:0000:00fe",
            "2620:00fe:0000:0000:0000:0000:0000:0009"
        ]
        DOH_SERVER = "https://dns.quad9.net/dns-query"
    elif _custom_dns == "cloudflare":
        CUSTOM_DNS = [
            "1.1.1.1", "1.0.0.1",
            "2606:4700:4700:0000:0000:0000:0000:1111",
            "2606:4700:4700:0000:0000:0000:0000:1001"
        ]
        DOH_SERVER = "https://cloudflare-dns.com/dns-query"
    elif _custom_dns == "opendns":
        CUSTOM_DNS = [
            "208.67.222.222", "208.67.220.220",
            "2620:0119:0035:0000:0000:0000:0000:0035",
            "2620:0119:0053:0000:0000:0000:0000:0053"
        ]
        DOH_SERVER = "https://doh.opendns.com/dns-query"
    else:
        # Custom DNS IPs
        _custom_dns_ips = _custom_dns.split(",")
        CUSTOM_DNS = [
            dns.strip() for dns in _custom_dns_ips 
            if dns.replace(":", "").replace(".", "").strip().isdigit()
        ]

# Apply DOH settings
if not USE_DOH:
    DOH_SERVER = ""

# ==============================================================================
# CUSTOM SCRIPT SETTINGS
# ==============================================================================

CUSTOM_SCRIPT = os.getenv("CUSTOM_SCRIPT", "").strip()

# Validate custom script
if CUSTOM_SCRIPT:
    if not os.path.exists(CUSTOM_SCRIPT):
        logger.warning(f"CUSTOM_SCRIPT {CUSTOM_SCRIPT} does not exist")
        CUSTOM_SCRIPT = ""
    elif not os.access(CUSTOM_SCRIPT, os.X_OK):
        logger.warning(f"CUSTOM_SCRIPT {CUSTOM_SCRIPT} is not executable")
        CUSTOM_SCRIPT = ""


# ==============================================================================
# LOGGING CONFIGURATION OUTPUT
# ==============================================================================

# Log all configuration values for debugging
for key, value in globals().items():
    if (not key.startswith('_') and 
        key.isupper() and 
        not callable(value) and
        key not in ['BASE_DIR', 'Path', 'os', 'json']):
        
        # Redact sensitive information
        if key == "AA_DONATOR_KEY" and value and value.strip():
            log_value = "REDACTED"
        else:
            log_value = value
        
        logger.info(f"{key}: {log_value}")

# Log computed values
logger.info(f"BASE_DIR: {BASE_DIR}")
logger.info(f"CROSS_FILE_SYSTEM: {CROSS_FILE_SYSTEM}")
logger.info(f"STAT TMP_DIR: {os.stat(TMP_DIR)}")
logger.info(f"STAT INGEST_DIR: {os.stat(INGEST_DIR)}")