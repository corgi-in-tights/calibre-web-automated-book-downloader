"""Centralized logging configuration for the book downloader application."""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Any


# TODO get rid of this bitch


def log_resource_usage(logger: logging.Logger) -> None:
    """Log current resource usage (memory and CPU)."""
    import psutil
    memory = psutil.virtual_memory()
    available_mb = memory.available / (1024 * 1024)
    memory_used_mb = memory.used / (1024 * 1024)
    cpu_percent = psutil.cpu_percent()
    logger.debug(f"Container Memory: Available={available_mb:.2f} MB, Used={memory_used_mb:.2f} MB, CPU: {cpu_percent:.2f}%")


def setup_logger(name: str, log_file: Path = None, log_level: str = "INFO", enable_logging: bool = True) -> logging.Logger:
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
    logger = logging.getLogger(name)
    
    # Set log level
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    log_level_obj = level_map.get(log_level.upper(), logging.INFO)
    logger.setLevel(log_level_obj)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )

    # Console handler for Docker output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level_obj)
    console_handler.addFilter(lambda record: record.levelno < logging.ERROR)  # Only allow logs below ERROR to stdout
    logger.addHandler(console_handler)
    
    # Error handler for stderr
    error_handler = logging.StreamHandler(sys.stderr)
    error_handler.setLevel(logging.ERROR) # Error and above go to stderr
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    # File handler if log file is specified and logging is enabled
    try:
        if enable_logging and log_file:
            # Create log directory if it doesn't exist
            log_dir = log_file.parent
            log_dir.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10485760,  # 10MB
                backupCount=5
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
    except Exception as e:
        logger.error(f"Failed to create log file: {e}", exc_info=True)

    return logger
