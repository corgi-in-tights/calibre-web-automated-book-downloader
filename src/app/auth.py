from functools import wraps

from utils.logger_utils import get_logger

logger = get_logger(__name__)

def login_required(f):
    """Decorator to require authentication for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        #TBD: Implement actual authentication check
        return f(*args, **kwargs)
    return decorated_function
