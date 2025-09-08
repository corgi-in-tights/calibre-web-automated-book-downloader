"""Flask application factory and configuration."""

import logging
import os
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from config.logger import setup_logger
from config.settings import (
    DEBUG, LOG_FILE, LOG_LEVEL, ENABLE_LOGGING
)


def create_app():
    """Create and configure Flask application."""
    # Initialize logger
    logger = setup_logger(__name__, LOG_FILE, LOG_LEVEL, ENABLE_LOGGING)
    
    # Create Flask app
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app)  # type: ignore
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching
    app.config['APPLICATION_ROOT'] = '/'
    
    # Set up authentication defaults
    # The secret key will reset every time we restart, which will
    # require users to authenticate again
    app.config.update(
        SECRET_KEY=os.urandom(64)
    )

    # Configure Flask logger
    app.logger.handlers = logger.handlers
    app.logger.setLevel(logger.level)
    
    # Also handle Werkzeug's logger
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.handlers = logger.handlers
    werkzeug_logger.setLevel(logger.level)

    # Register blueprints
    from .routes import main_bp
    app.register_blueprint(main_bp)
    
    # Register dual routes (with /request prefix)
    register_dual_routes(app)
    
    logger.log_resource_usage()
    
    return app


def register_dual_routes(app: Flask) -> None:
    """
    Register each route both with and without the /request prefix.
    This function should be called after all routes are defined.
    """
    import typing
    from flask import url_for as flask_url_for
    
    # Store original url_map rules
    rules = list(app.url_map.iter_rules())
    
    # Add /request prefix to each rule
    for rule in rules:
        if rule.rule != '/request/' and rule.rule != '/request':  # Skip if it's already a request route
            # Create new routes with /request prefix, both with and without trailing slash
            base_rule = rule.rule[:-1] if rule.rule.endswith('/') else rule.rule
            if base_rule == '':  # Special case for root path
                app.add_url_rule('/request', f"root_request", 
                               view_func=app.view_functions[rule.endpoint],
                               methods=rule.methods)
                app.add_url_rule('/request/', f"root_request_slash", 
                               view_func=app.view_functions[rule.endpoint],
                               methods=rule.methods)
            else:
                app.add_url_rule(f"/request{base_rule}", 
                               f"{rule.endpoint}_request",
                               view_func=app.view_functions[rule.endpoint],
                               methods=rule.methods)
                app.add_url_rule(f"/request{base_rule}/", 
                               f"{rule.endpoint}_request_slash",
                               view_func=app.view_functions[rule.endpoint],
                               methods=rule.methods)
    
    def url_for_with_request(endpoint: str, **values: typing.Any) -> str:
        """Generate URLs with /request prefix by default."""
        if endpoint == 'static':
            # For static files, add /request prefix
            url = flask_url_for(endpoint, **values)
            return f"/request{url}"
        return flask_url_for(endpoint, **values)
    
    app.jinja_env.globals['url_for'] = url_for_with_request
