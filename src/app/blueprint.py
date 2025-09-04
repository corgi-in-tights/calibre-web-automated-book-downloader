"""Flask Blueprint with route definitions."""

from functools import wraps
from flask import Blueprint, Response

from config.settings import CWA_DB_PATH, DEBUG
from .views import (
    authenticate, index_view, favicon_view, debug_view, restart_view,
    api_search_view, api_info_view, api_download_view, api_status_view,
    api_local_download_view, api_cancel_download_view, api_set_priority_view,
    api_reorder_queue_view, api_queue_order_view, api_active_downloads_view,
    api_clear_completed_view, not_found_error_handler, internal_error_handler
)

# Create main blueprint
main_bp = Blueprint('main', __name__)


def login_required(f):
    """Decorator to require authentication for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If the CWA_DB_PATH variable exists, but isn't a valid
        # path, return a server error
        import os
        if CWA_DB_PATH is not None and not os.path.isfile(CWA_DB_PATH):
            from config.logger import setup_logger
            from config.settings import LOG_FILE, LOG_LEVEL, ENABLE_LOGGING
            logger = setup_logger(__name__, LOG_FILE, LOG_LEVEL, ENABLE_LOGGING)
            logger.error(f"CWA_DB_PATH is set to {CWA_DB_PATH} but this is not a valid path")
            return Response("Internal Server Error", 500)
        if not authenticate():
            return Response(
                response="Unauthorized",
                status=401,
                headers={
                    "WWW-Authenticate": 'Basic realm="Calibre-Web-Automated-Book-Downloader"',
                },
            )
        return f(*args, **kwargs)
    return decorated_function


# Main routes
@main_bp.route('/')
@login_required
def index():
    """Render main page with search and status table."""
    return index_view()


@main_bp.route('/favico<path:_>')
@main_bp.route('/request/favico<path:_>')
@main_bp.route('/request/static/favico<path:_>')
def favicon(_):
    """Serve favicon."""
    return favicon_view(_)


# Debug routes (only available when DEBUG is True)
if DEBUG:
    @main_bp.route('/debug', methods=['GET'])
    @login_required
    def debug():
        """Generate and return debug information."""
        return debug_view()

    @main_bp.route('/api/restart', methods=['GET'])
    @login_required
    def restart():
        """Restart the application."""
        return restart_view()


# API routes
@main_bp.route('/api/search', methods=['GET'])
@login_required
def api_search():
    """Search for books matching the provided query."""
    return api_search_view()


@main_bp.route('/api/info', methods=['GET'])
@login_required
def api_info():
    """Get detailed book information."""
    return api_info_view()


@main_bp.route('/api/download', methods=['GET'])
@login_required
def api_download():
    """Queue a book for download."""
    return api_download_view()


@main_bp.route('/api/status', methods=['GET'])
@login_required
def api_status():
    """Get current download queue status."""
    return api_status_view()


@main_bp.route('/api/localdownload', methods=['GET'])
@login_required
def api_local_download():
    """Download an EPUB file from local storage if available."""
    return api_local_download_view()


@main_bp.route('/api/download/<book_id>/cancel', methods=['DELETE'])
@login_required
def api_cancel_download(book_id: str):
    """Cancel a download."""
    return api_cancel_download_view(book_id)


@main_bp.route('/api/queue/<book_id>/priority', methods=['PUT'])
@login_required
def api_set_priority(book_id: str):
    """Set priority for a queued book."""
    return api_set_priority_view(book_id)


@main_bp.route('/api/queue/reorder', methods=['POST'])
@login_required
def api_reorder_queue():
    """Bulk reorder queue by setting new priorities."""
    return api_reorder_queue_view()


@main_bp.route('/api/queue/order', methods=['GET'])
@login_required
def api_queue_order():
    """Get current queue order for display."""
    return api_queue_order_view()


@main_bp.route('/api/downloads/active', methods=['GET'])
@login_required
def api_active_downloads():
    """Get list of currently active downloads."""
    return api_active_downloads_view()


@main_bp.route('/api/queue/clear', methods=['DELETE'])
@login_required
def api_clear_completed():
    """Clear all completed, errored, or cancelled books from tracking."""
    return api_clear_completed_view()


# Error handlers
@main_bp.errorhandler(404)
def not_found_error(error):
    """Handle 404 (Not Found) errors."""
    return not_found_error_handler(error)


@main_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 (Internal Server) errors."""
    return internal_error_handler(error)
