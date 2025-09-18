import logging

from src.conf import settings


def log_container_resource_usage(logger: logging.Logger) -> None:
    """Log current resource usage (memory and CPU) for Docker debugging."""
    # Debug dependency
    try:
        import psutil  # type: ignore  # noqa: PGH003, PLC0415
    except ImportError:
        logger.warning("psutil not installed, cannot log resource usage.")
        return

    memory = psutil.virtual_memory()
    available_mb = memory.available / (1024 * 1024)
    memory_used_mb = memory.used / (1024 * 1024)
    cpu_percent = psutil.cpu_percent()
    logger.debug(
        "Container Memory: Available=%.2f MB, Used=%.2f MB, CPU: %.2f%%",
        available_mb,
        memory_used_mb,
        cpu_percent,
    )


def log_debug_keys(logger: logging.Logger) -> None:
    """Log specific debug configuration keys."""

    def redact_values(key: str, value):
        if not key.isupper():
            return "PRIVATE"
        if key.startswith("_") or key.strip() == "AA_DONATOR_KEY":
            return "REDACTED"
        return value

    for key in settings.DEBUG_LOG_KEYS:
        value = getattr(settings, key, None)
        if value is not None:
            if not callable(value):
                logger.debug("Logging debug key: %s: %s", key, redact_values(key, value))
        else:
            logger.debug("Logging debug key: %s not set", key)
