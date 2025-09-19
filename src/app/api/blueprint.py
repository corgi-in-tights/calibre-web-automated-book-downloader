import io
import logging
import re

from flask import Blueprint, jsonify, request, send_file
from werkzeug.wrappers import Response

from app.auth import login_required
from models import SearchFilters
from services import book_service

bp = Blueprint("api", __name__, url_prefix="/api")
logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# GENERAL API INFO
# ----------------------------------------------------------------------
@bp.route("/status", methods=["GET"])
@login_required
def api_status_view() -> Response | tuple[Response, int]:
    """Get current download queue status."""
    try:
        status = book_service.queue_status()
        return jsonify(status)
    except Exception as e:
        logger.exception("Status error")
        return jsonify({"error": str(e)}), 500


# ----------------------------------------------------------------------
# GENERAL BOOK SEARCH/INFO
# ----------------------------------------------------------------------
@bp.route("/search", methods=["GET"])
@login_required
def api_search_view() -> Response | tuple[Response, int]:
    """Search for books matching query/filters."""
    query = request.args.get("query", "")
    filters = SearchFilters(
        isbn=request.args.getlist("isbn"),
        author=request.args.getlist("author"),
        title=request.args.getlist("title"),
        lang=request.args.getlist("lang"),
        sort=request.args.get("sort"),
        content=request.args.getlist("content"),
        format=request.args.getlist("format"),
    )

    if not query and not any(vars(filters).values()):
        return jsonify([])

    try:
        books = book_service.search_books(query, filters)
        return jsonify(books)
    except Exception as e:
        logger.exception("Failed to search for book")
        return jsonify({"error": str(e)}), 500


@bp.route("/info", methods=["GET"])
@login_required
def api_info_view() -> Response | tuple[Response, int]:
    """Get detailed book information by ID."""
    book_id = request.args.get("id", "")
    if not book_id:
        return jsonify({"error": "No book ID provided"}), 400

    try:
        book = book_service.get_book_info(book_id)
        if book:
            return jsonify(book)
        return jsonify({"error": "Book not found"}), 404
    except Exception as e:
        logger.exception("Info error")
        return jsonify({"error": str(e)}), 500



# ----------------------------------------------------------------------
# BOOK DOWNLOADING
# ----------------------------------------------------------------------
@bp.route("/download", methods=["GET"])
@login_required
def api_download_view() -> Response | tuple[Response, int]:
    """Queue a book for download by ID."""
    book_id = request.args.get("id", "")
    if not book_id:
        return jsonify({"error": "No book ID provided"}), 400

    try:
        priority = int(request.args.get("priority", 0))
        success = backend.queue_book(book_id, priority)
        if success:
            return jsonify({"status": "queued", "priority": priority})
        return jsonify({"error": "Failed to queue book"}), 500
    except Exception as e:
        logger.exception("Download error")
        return jsonify({"error": str(e)}), 500

@bp.route("/local_download", methods=["GET"])
@login_required
def api_local_download_view() -> Response | tuple[Response, int]:
    """Download a local EPUB file if available."""
    book_id = request.args.get("id", "")
    if not book_id:
        return jsonify({"error": "No book ID provided"}), 400

    try:
        file_data, book_info = backend.get_book_data(book_id)
        if file_data is None:
            return jsonify({"error": "File not found"}), 404

        # Sanitize filename
        file_name = re.sub(r"[\\/:*?\"<>|]", "_", book_info.title.strip())[:245]
        file_extension = book_info.format

        return send_file(
            io.BytesIO(file_data),
            download_name=f"{file_name}.{file_extension}",
            as_attachment=True,
        )
    except Exception as e:
        logger.exception("Local download error")
        return jsonify({"error": str(e)}), 500

@bp.route("/downloads/active", methods=["GET"])
@login_required
def api_active_downloads_view() -> Response | tuple[Response, int]:
    """Get list of currently active downloads."""
    try:
        active_downloads = backend.get_active_downloads()
        return jsonify({"active_downloads": active_downloads})
    except Exception as e:
        logger.exception("Active downloads error")
        return jsonify({"error": str(e)}), 500

@bp.route("/download/<book_id>/cancel", methods=["DELETE"])
@login_required
def api_cancel_download_view(book_id: str) -> Response | tuple[Response, int]:
    """Cancel a queued or active download."""
    try:
        success = backend.cancel_download(book_id)
        if success:
            return jsonify({"status": "cancelled", "book_id": book_id})
        return jsonify({"error": "Failed to cancel download or book not found"}), 404
    except Exception as e:
        logger.exception("Cancel download error")
        return jsonify({"error": str(e)}), 500


# ----------------------------------------------------------------------
# QUEUE MANAGEMENT/PRIORITY
# ----------------------------------------------------------------------

@bp.route("/queue/<book_id>/priority", methods=["PUT"])
@login_required
def api_set_priority_view(book_id: str) -> Response | tuple[Response, int]:
    """Set priority for a queued book."""
    try:
        data = request.get_json()
        if not data or "priority" not in data:
            return jsonify({"error": "Priority not provided"}), 400

        priority = int(data["priority"])
        success = backend.set_book_priority(book_id, priority)
        if success:
            return jsonify({"status": "updated", "book_id": book_id, "priority": priority})
        return jsonify({"error": "Failed to update priority or book not found"}), 404
    except ValueError:
        return jsonify({"error": "Invalid priority value"}), 400
    except Exception as e:
        logger.exception("Set priority error")
        return jsonify({"error": str(e)}), 500


@bp.route("/queue/reorder", methods=["POST"])
@login_required
def api_reorder_queue_view() -> Response | tuple[Response, int]:
    """Bulk reorder queue by setting new priorities."""
    try:
        data = request.get_json()
        if not data or "book_priorities" not in data:
            return jsonify({"error": "book_priorities not provided"}), 400

        book_priorities = data["book_priorities"]
        if not isinstance(book_priorities, dict):
            return jsonify({"error": "book_priorities must be a dictionary"}), 400

        # Validate all priorities are ints
        if not all(isinstance(priority, int) for priority in book_priorities.values()):
            return jsonify({"error": "All priorities must be integers"}), 400

        success = backend.reorder_queue(book_priorities)
        if success:
            return jsonify({"status": "reordered", "updated_count": len(book_priorities)})
        return jsonify({"error": "Failed to reorder queue"}), 500
    except Exception as e:
        logger.exception("Reorder queue error")
        return jsonify({"error": str(e)}), 500


@bp.route("/queue/order", methods=["GET"])
@login_required
def api_queue_order_view() -> Response | tuple[Response, int]:
    """Get current queue order for display."""
    try:
        queue_order = backend.get_queue_order()
        return jsonify({"queue": queue_order})
    except Exception as e:
        logger.exception("Queue order error")
        return jsonify({"error": str(e)}), 500


@bp.route("/queue/clear", methods=["DELETE"])
@login_required
def api_clear_completed_view() -> Response | tuple[Response, int]:
    """Clear all completed/errored/cancelled books from queue."""
    try:
        removed_count = backend.clear_completed()
        return jsonify({"status": "cleared", "removed_count": removed_count})
    except Exception as e:
        logger.exception("Clear completed error")
        return jsonify({"error": str(e)}), 500


# ----------------------------------------------------------------------
# ERROR HANDLERS
# ----------------------------------------------------------------------
@bp.errorhandler(404)
def not_found_error_handler(error: Exception) -> Response | tuple[Response, int]:
    logger.warning("404 route not found for URL %s", request.url, exc_info=error)
    return jsonify({"error": "Resource not found"}), 404

@bp.errorhandler(500)
def internal_error_handler(error: Exception) -> Response | tuple[Response, int]:
    logger.exception("Internal server error", exc_info=error)
    return jsonify({"error": "Internal server error"}), 500
