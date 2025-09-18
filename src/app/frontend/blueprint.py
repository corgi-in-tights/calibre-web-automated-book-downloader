from pathlib import Path

from flask import Blueprint, render_template, send_from_directory

from app.auth import login_required
from conf import settings

bp = Blueprint("frontend", __name__)

@bp.route("/")
@login_required
def index():
    """Render main page with search and status table."""
    return render_template(
        "index.html",
        book_languages=settings.SUPPORTED_BOOK_LANGUAGES,
        default_language=settings.DEFAULT_BOOK_LANGUAGE,
        debug=settings.DEBUG,
        build_version=settings.BUILD_VERSION,
        release_version=settings.RELEASE_VERSION,
        app_env=settings.APP_ENV,
    )


@bp.route("/favico<path:_>")
@bp.route("/request/favico<path:_>")
@bp.route("/request/static/favico<path:_>")
def favicon(_):
    """Serve favicon from static media directory."""
    from flask import current_app  # noqa: PLC0415
    return send_from_directory(
        Path(current_app.root_path) / "static" / "media", "favicon.ico", mimetype="image/vnd.microsoft.icon",
    )
