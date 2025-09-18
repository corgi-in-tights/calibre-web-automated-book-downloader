import logging
import os
import signal
import subprocess
import time

from flask import Blueprint, jsonify, send_file

from app.auth import login_required
from conf import settings

bp = Blueprint("debug", __name__, url_prefix="/debug")
logger = logging.getLogger(__name__)


def get_stop_gui():
    if settings.USING_EXTERNAL_BYPASSER:
        return lambda: None  # No-op for external bypasser
    from services.cf_bypasser import get_bypasser as _get_bypasser

    return _get_bypasser()


@bp.route("/debug", methods=["GET"])
@login_required
def debug():
    """
    This will run the /app/debug.sh script, which will generate a debug zip with all the logs
    The file will be named /tmp/cwa-book-downloader-debug.zip
    And then return it to the user
    """
    try:
        # Run the debug script
        STOP_GUI()
        time.sleep(1)
        result = subprocess.run(["/app/genDebug.sh"], capture_output=True, text=True, check=True)
        if result.returncode != 0:
            raise Exception(f"Debug script failed: {result.stderr}")
        logger.info(f"Debug script executed: {result.stdout}")
        debug_file_path = result.stdout.strip().split("\n")[-1]
        if not os.path.exists(debug_file_path):
            logger.error("Debug zip file not found after running debug script")
            return jsonify({"error": "Failed to generate debug information"}), 500

        # Return the file to the user
        return send_file(
            debug_file_path,
            mimetype="application/zip",
            download_name=os.path.basename(debug_file_path),
            as_attachment=True,
        )
    except subprocess.CalledProcessError as e:
        logger.error_trace(f"Debug script error: {e}, stdout: {e.stdout}, stderr: {e.stderr}")
        return jsonify({"error": f"Debug script failed: {e.stderr}"}), 500
    except Exception as e:
        logger.error_trace(f"Debug endpoint error: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/shutdown", methods=["GET", "POST"])
@login_required
def shutdown():
    os.kill(os.getpid(), signal.SIGTERM)  # gracefully kill workers
    return {"status": "Shutting down gracefully..."}, 202
