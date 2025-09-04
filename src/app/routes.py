"""Main application entry point."""

from app import create_app
from config.settings import FLASK_HOST, FLASK_PORT, DEBUG, APP_ENV
from config.logger import setup_logger
from config.settings import LOG_FILE, LOG_LEVEL, ENABLE_LOGGING

logger = setup_logger(__name__, LOG_FILE, LOG_LEVEL, ENABLE_LOGGING)

# Create Flask application
app = create_app()

if __name__ == '__main__':
    logger.info(f"Starting Flask application on {FLASK_HOST}:{FLASK_PORT} IN {APP_ENV} mode")
    app.run(
        host=FLASK_HOST,
        port=FLASK_PORT,
        debug=DEBUG 
    )
