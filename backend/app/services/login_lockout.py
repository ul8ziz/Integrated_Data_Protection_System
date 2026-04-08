"""
Login lockout helpers: failed attempt counter and temporary account lock.
"""
import math
from datetime import datetime, timedelta
from app.config import settings
from app.models_mongo.users import User
from app.utils.datetime_utils import get_current_time, ensure_aware_for_compare


def _now() -> datetime:
    return get_current_time()


def clear_expired_lock(user: User, now: datetime) -> bool:
    """Reset counter and lock if the lock window has ended. Returns True if user was modified."""
    locked_until = ensure_aware_for_compare(user.locked_until)
    if locked_until is None:
        return False
    if locked_until <= now:
        user.failed_login_attempts = 0
        user.locked_until = None
        return True
    return False


def retry_after_seconds(user: User, now: datetime) -> int:
    """Seconds remaining until lock expires (at least 1 if still locked)."""
    locked_until = ensure_aware_for_compare(user.locked_until)
    if locked_until is None or locked_until <= now:
        return 0
    delta = locked_until - now
    return max(1, int(math.ceil(delta.total_seconds())))


def reset_lockout_on_success(user: User) -> None:
    user.failed_login_attempts = 0
    user.locked_until = None


def record_failed_password(user: User) -> bool:
    """
    Increment failed attempts; set locked_until when threshold reached.

    Returns:
        True when this attempt triggered the lock (should respond with 429).
    """
    max_attempts = max(1, settings.LOGIN_MAX_FAILED_ATTEMPTS)
    lock_seconds = max(1, settings.LOGIN_LOCKOUT_SECONDS)

    user.failed_login_attempts = user.failed_login_attempts + 1
    now = _now()
    if user.failed_login_attempts >= max_attempts:
        user.locked_until = now + timedelta(seconds=lock_seconds)
        return True
    return False
