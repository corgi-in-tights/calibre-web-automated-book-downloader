import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(log_file: Path | None = None, log_level: str = "INFO") -> logging.Logger:
    """Set up and configure a logger instance.

    Args:
        name: The name of the logger instance
        log_file: Optional path to log file. If None, logs only to stdout/stderr
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_logging: Whether to enable file logging

    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logger
    logger = logging.getLogger()

    # Set log level
    log_level_obj = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(log_level_obj)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s")

    # Console for stdout (below ERROR only)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level_obj)
    console_handler.addFilter(lambda record: record.levelno < logging.ERROR)
    logger.addHandler(console_handler)

    # Error handler for stderr (ERROR and above)
    error_handler = logging.StreamHandler(sys.stderr)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)

    # File handler if log file is specified and logging is enabled
    try:
        if log_file:
            # Create log directory if it doesn't exist
            log_dir = log_file.parent
            log_dir.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10485760,  # 10MB
                backupCount=5,
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
    except Exception:
        logger.exception("Failed to create log file: %s")

    return logger

def get_logger(name: str, project_root_name: str | None = None) -> logging.Logger:
    """Get a logger instance by name.

    Args:
        name: The name of the logger instance

    Returns:
        logging.Logger: Logger instance
    """
    root_prefix = project_root_name if project_root_name else "cwa_bd."
    return logging.getLogger(root_prefix + name)
