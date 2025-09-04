"""Business logic and view handlers for the Flask application."""

import os
import re
import io
import sqlite3
import subprocess
import time
from typing import Union, Tuple, Any

from flask import request, jsonify, render_template, send_file, send_from_directory
from werkzeug.security import check_password_hash
from werkzeug.wrappers import Response

from config.logger import setup_logger
from config.settings import (
    _SUPPORTED_BOOK_LANGUAGES, BOOK_LANGUAGE, CWA_DB_PATH, DEBUG, 
    USING_EXTERNAL_BYPASSER, BUILD_VERSION, RELEASE_VERSION, APP_ENV,
    LOG_FILE, LOG_LEVEL, ENABLE_LOGGING
)
import src.services.backend as backend
from src.services.models import SearchFilters

logger = setup_logger(__name__, LOG_FILE, LOG_LEVEL, ENABLE_LOGGING)

# Initialize debug functions if needed
if DEBUG:
    if USING_EXTERNAL_BYPASSER:
        STOP_GUI = lambda: None  # No-op for external bypasser
    else:
        from cloudflare_bypasser import _reset_driver as STOP_GUI


def authenticate() -> bool:
    """
    Helper function that validates Basic credentials
    against a Calibre-Web app.db SQLite database

    Database structure:
    - Table 'user' with columns: 'name' (username), 'password'
    """
    # If the database doesn't exist, the user is always authenticated
    if not CWA_DB_PATH:
        return True

    # If no authorization object exists, return false to prompt
    # a request to the user
    if not request.authorization:
        return False

    username = request.authorization.get("username")
    password = request.authorization.get("password")

    # Validate credentials against database
    try:
        # Open database in true read-only mode to avoid journal/WAL writes on RO mounts
        db_path = os.fspath(CWA_DB_PATH)
        db_uri = f"file:{db_path}?mode=ro&immutable=1"
        conn = sqlite3.connect(db_uri, uri=True)
        cur = conn.cursor()
        cur.execute("SELECT password FROM user WHERE name = ?", (username,))
        row = cur.fetchone()
        conn.close()

        # Check if user exists and password is correct
        if not row or not row[0] or not check_password_hash(row[0], password):
            logger.error("User not found or password check failed")
            return False

    except Exception as e:
        logger.error_trace(f"CWA DB or authentication error: {e}")
        return False

    logger.info(f"Authentication successful for user {username}")
    return True


def index_view() -> str:
    """Render main page with search and status table."""
    return render_template('index.html', 
                           book_languages=_SUPPORTED_BOOK_LANGUAGES, 
                           default_language=BOOK_LANGUAGE, 
                           debug=DEBUG,
                           build_version=BUILD_VERSION,
                           release_version=RELEASE_VERSION,
                           app_env=APP_ENV
                           )


def favicon_view(_: Any) -> Response:
    """Serve favicon from static media directory."""
    from flask import current_app
    return send_from_directory(os.path.join(current_app.root_path, 'static', 'media'),
        'favicon.ico', mimetype='image/vnd.microsoft.icon')


def debug_view() -> Union[Response, Tuple[Response, int]]:
    """
    Generate and return debug information zip file.
    Only available when DEBUG is True.
    """
    try:
        # Run the debug script
        STOP_GUI()
        time.sleep(1)
        result = subprocess.run(['/app/genDebug.sh'], capture_output=True, text=True, check=True)
        if result.returncode != 0:
            raise Exception(f"Debug script failed: {result.stderr}")
        logger.info(f"Debug script executed: {result.stdout}")
        debug_file_path = result.stdout.strip().split('\n')[-1]
        if not os.path.exists(debug_file_path):
            logger.error("Debug zip file not found after running debug script")
            return jsonify({"error": "Failed to generate debug information"}), 500
            
        # Return the file to the user
        return send_file(
            debug_file_path,
            mimetype='application/zip',
            download_name=os.path.basename(debug_file_path),
            as_attachment=True
        )
    except subprocess.CalledProcessError as e:
        logger.error_trace(f"Debug script error: {e}, stdout: {e.stdout}, stderr: {e.stderr}")
        return jsonify({"error": f"Debug script failed: {e.stderr}"}), 500
    except Exception as e:
        logger.error_trace(f"Debug endpoint error: {e}")
        return jsonify({"error": str(e)}), 500


def restart_view() -> Union[Response, Tuple[Response, int]]:
    """Restart the application. Only available when DEBUG is True."""
    os._exit(0)


def api_search_view() -> Union[Response, Tuple[Response, int]]:
    """
    Search for books matching the provided query.

    Query Parameters:
        query (str): Search term (ISBN, title, author, etc.)
        isbn (str): Book ISBN
        author (str): Book Author
        title (str): Book Title
        lang (str): Book Language
        sort (str): Order to sort results
        content (str): Content type of book
        format (str): File format filter (pdf, epub, mobi, azw3, fb2, djvu, cbz, cbr)

    Returns:
        flask.Response: JSON array of matching books or error response.
    """
    query = request.args.get('query', '')

    filters = SearchFilters(
        isbn = request.args.getlist('isbn'),
        author = request.args.getlist('author'),
        title = request.args.getlist('title'),
        lang = request.args.getlist('lang'),
        sort = request.args.get('sort'),
        content = request.args.getlist('content'),
        format = request.args.getlist('format'),
    )

    if not query and not any(vars(filters).values()):
        return jsonify([])

    try:
        books = backend.search_books(query, filters)
        return jsonify(books)
    except Exception as e:
        logger.error_trace(f"Search error: {e}")
        return jsonify({"error": str(e)}), 500


def api_info_view() -> Union[Response, Tuple[Response, int]]:
    """
    Get detailed book information.

    Query Parameters:
        id (str): Book identifier (MD5 hash)

    Returns:
        flask.Response: JSON object with book details, or an error message.
    """
    book_id = request.args.get('id', '')
    if not book_id:
        return jsonify({"error": "No book ID provided"}), 400

    try:
        book = backend.get_book_info(book_id)
        if book:
            return jsonify(book)
        return jsonify({"error": "Book not found"}), 404
    except Exception as e:
        logger.error_trace(f"Info error: {e}")
        return jsonify({"error": str(e)}), 500


def api_download_view() -> Union[Response, Tuple[Response, int]]:
    """
    Queue a book for download.

    Query Parameters:
        id (str): Book identifier (MD5 hash)

    Returns:
        flask.Response: JSON status object indicating success or failure.
    """
    book_id = request.args.get('id', '')
    if not book_id:
        return jsonify({"error": "No book ID provided"}), 400

    try:
        priority = int(request.args.get('priority', 0))
        success = backend.queue_book(book_id, priority)
        if success:
            return jsonify({"status": "queued", "priority": priority})
        return jsonify({"error": "Failed to queue book"}), 500
    except Exception as e:
        logger.error_trace(f"Download error: {e}")
        return jsonify({"error": str(e)}), 500


def api_status_view() -> Union[Response, Tuple[Response, int]]:
    """
    Get current download queue status.

    Returns:
        flask.Response: JSON object with queue status.
    """
    try:
        status = backend.queue_status()
        return jsonify(status)
    except Exception as e:
        logger.error_trace(f"Status error: {e}")
        return jsonify({"error": str(e)}), 500


def api_local_download_view() -> Union[Response, Tuple[Response, int]]:
    """
    Download an EPUB file from local storage if available.

    Query Parameters:
        id (str): Book identifier (MD5 hash)

    Returns:
        flask.Response: The EPUB file if found, otherwise an error response.
    """
    book_id = request.args.get('id', '')
    if not book_id:
        return jsonify({"error": "No book ID provided"}), 400

    try:
        file_data, book_info = backend.get_book_data(book_id)
        if file_data is None:
            # Book data not found or not available
            return jsonify({"error": "File not found"}), 404
        # Sanitize the file name
        file_name = book_info.title
        file_name = re.sub(r'[\\/:*?"<>|]', '_', file_name.strip())[:245]
        file_extension = book_info.format
        # Prepare the file for sending to the client
        data = io.BytesIO(file_data)
        return send_file(
            data,
            download_name=f"{file_name}.{file_extension}",
            as_attachment=True
        )

    except Exception as e:
        logger.error_trace(f"Local download error: {e}")
        return jsonify({"error": str(e)}), 500


def api_cancel_download_view(book_id: str) -> Union[Response, Tuple[Response, int]]:
    """
    Cancel a download.

    Path Parameters:
        book_id (str): Book identifier to cancel

    Returns:
        flask.Response: JSON status indicating success or failure.
    """
    try:
        success = backend.cancel_download(book_id)
        if success:
            return jsonify({"status": "cancelled", "book_id": book_id})
        return jsonify({"error": "Failed to cancel download or book not found"}), 404
    except Exception as e:
        logger.error_trace(f"Cancel download error: {e}")
        return jsonify({"error": str(e)}), 500


def api_set_priority_view(book_id: str) -> Union[Response, Tuple[Response, int]]:
    """
    Set priority for a queued book.

    Path Parameters:
        book_id (str): Book identifier

    Request Body:
        priority (int): New priority level (lower number = higher priority)

    Returns:
        flask.Response: JSON status indicating success or failure.
    """
    try:
        data = request.get_json()
        if not data or 'priority' not in data:
            return jsonify({"error": "Priority not provided"}), 400
            
        priority = int(data['priority'])
        success = backend.set_book_priority(book_id, priority)
        
        if success:
            return jsonify({"status": "updated", "book_id": book_id, "priority": priority})
        return jsonify({"error": "Failed to update priority or book not found"}), 404
    except ValueError:
        return jsonify({"error": "Invalid priority value"}), 400
    except Exception as e:
        logger.error_trace(f"Set priority error: {e}")
        return jsonify({"error": str(e)}), 500


def api_reorder_queue_view() -> Union[Response, Tuple[Response, int]]:
    """
    Bulk reorder queue by setting new priorities.

    Request Body:
        book_priorities (dict): Mapping of book_id to new priority

    Returns:
        flask.Response: JSON status indicating success or failure.
    """
    try:
        data = request.get_json()
        if not data or 'book_priorities' not in data:
            return jsonify({"error": "book_priorities not provided"}), 400
            
        book_priorities = data['book_priorities']
        if not isinstance(book_priorities, dict):
            return jsonify({"error": "book_priorities must be a dictionary"}), 400
            
        # Validate all priorities are integers
        for book_id, priority in book_priorities.items():
            if not isinstance(priority, int):
                return jsonify({"error": f"Invalid priority for book {book_id}"}), 400
                
        success = backend.reorder_queue(book_priorities)
        
        if success:
            return jsonify({"status": "reordered", "updated_count": len(book_priorities)})
        return jsonify({"error": "Failed to reorder queue"}), 500
    except Exception as e:
        logger.error_trace(f"Reorder queue error: {e}")
        return jsonify({"error": str(e)}), 500


def api_queue_order_view() -> Union[Response, Tuple[Response, int]]:
    """
    Get current queue order for display.

    Returns:
        flask.Response: JSON array of queued books with their order and priorities.
    """
    try:
        queue_order = backend.get_queue_order()
        return jsonify({"queue": queue_order})
    except Exception as e:
        logger.error_trace(f"Queue order error: {e}")
        return jsonify({"error": str(e)}), 500


def api_active_downloads_view() -> Union[Response, Tuple[Response, int]]:
    """
    Get list of currently active downloads.

    Returns:
        flask.Response: JSON array of active download book IDs.
    """
    try:
        active_downloads = backend.get_active_downloads()
        return jsonify({"active_downloads": active_downloads})
    except Exception as e:
        logger.error_trace(f"Active downloads error: {e}")
        return jsonify({"error": str(e)}), 500


def api_clear_completed_view() -> Union[Response, Tuple[Response, int]]:
    """
    Clear all completed, errored, or cancelled books from tracking.

    Returns:
        flask.Response: JSON with count of removed books.
    """
    try:
        removed_count = backend.clear_completed()
        return jsonify({"status": "cleared", "removed_count": removed_count})
    except Exception as e:
        logger.error_trace(f"Clear completed error: {e}")
        return jsonify({"error": str(e)}), 500


def not_found_error_handler(error: Exception) -> Union[Response, Tuple[Response, int]]:
    """
    Handle 404 (Not Found) errors.

    Args:
        error (HTTPException): The 404 error raised by Flask.

    Returns:
        flask.Response: JSON error message with 404 status.
    """
    logger.warning(f"404 error: {request.url} : {error}")
    return jsonify({"error": "Resource not found"}), 404


def internal_error_handler(error: Exception) -> Union[Response, Tuple[Response, int]]:
    """
    Handle 500 (Internal Server) errors.

    Args:
        error (HTTPException): The 500 error raised by Flask.

    Returns:
        flask.Response: JSON error message with 500 status.
    """
    logger.error_trace(f"500 error: {error}")
    return jsonify({"error": "Internal server error"}), 500
