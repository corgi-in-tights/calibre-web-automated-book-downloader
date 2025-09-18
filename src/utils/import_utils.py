import importlib
import logging

logger = logging.getLogger(__name__)

def load_module_by_name(name: str, logger: logging.Logger = logger) -> None:
    """
    Uses importlib to load a module by its name.
    Args:
        name: The name of the module to load.
    """
    try:
        importlib.import_module(name)
        logger.debug("Successfully loaded module: %s", name)
    except ImportError:
        logger.exception("Failed to load module %s", name)
        raise
