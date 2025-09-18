import logging

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from conf import settings
from utils import setup_logger
from utils.import_utils import load_module_by_name
from utils.logger_utils import get_logger

BLUEPRINT_PATHS = ["app.api", "app.frontend"]

def create_app():
    """Create and configure Flask application."""
    # Initialize logger
    log_file = settings.LOG_FILE if settings.ENABLE_FILE_LOGGING else None
    setup_logger(log_file, settings.LOG_LEVEL)
    logger = get_logger(__name__)

    # Create Flask app
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app)
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0  # Disable caching
    app.config["APPLICATION_ROOT"] = "/"

    app.config.update(SECRET_KEY=settings.SECRET_KEY)

    # Configure Flask logger
    app.logger.handlers = logger.handlers
    app.logger.setLevel(logger.level)

    blueprint_paths = BLUEPRINT_PATHS.copy() + (["app.debug"] if settings.DEBUG else [])
    for bp_path in blueprint_paths:
        try:
            bp_module = load_module_by_name(bp_path)
        except ImportError:
            logger.exception("Failed to load blueprint module %s", bp_path)
            continue

        app.register_blueprint(bp_module.bp)
        logger.debug("Registered blueprint: %s", bp_path)

    # Also handle Werkzeug's logger
    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.handlers = logger.handlers
    werkzeug_logger.setLevel(logger.level)

    if settings.DEBUG:
        from utils.debug_utils import log_container_resource_usage  # noqa: PLC0415
        log_container_resource_usage(logger)

    return app

