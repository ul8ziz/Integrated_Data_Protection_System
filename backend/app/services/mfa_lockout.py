"""
MFA / TOTP verification lockout (brute-force mitigation on 6-digit codes).
"""
import math
from datetime import datetime, timedelta

from app.config import settings
from app.models_mongo.users import User
from app.utils.datetime_utils import get_current_time, ensure_aware_for_compare


def _now() -> datetime:
    return get_current_time()


def clear_expired_mfa_lock(user: User, now: datetime) -> bool:
    """Reset MFA counter and lock if the lock window has ended."""
    locked_until = ensure_aware_for_compare(user.mfa_locked_until)
    if locked_until is None:
        return False
    if locked_until <= now:
        user.mfa_failed_attempts = 0
        user.mfa_locked_until = None
        return True
    return False


def mfa_retry_after_seconds(user: User, now: datetime) -> int:
    locked_until = ensure_aware_for_compare(user.mfa_locked_until)
    if locked_until is None or locked_until <= now:
        return 0
    delta = locked_until - now
    return max(1, int(math.ceil(delta.total_seconds())))


def reset_mfa_lockout_on_success(user: User) -> None:
    user.mfa_failed_attempts = 0
    user.mfa_locked_until = None


def record_failed_mfa(user: User) -> bool:
    """
    Increment failed MFA attempts; set mfa_locked_until when threshold reached.
    Returns True when this attempt triggered the lock.
    """
    max_attempts = max(1, settings.MFA_MAX_FAILED_ATTEMPTS)
    lock_seconds = max(1, settings.MFA_LOCKOUT_SECONDS)

    user.mfa_failed_attempts = user.mfa_failed_attempts + 1
    now = _now()
    if user.mfa_failed_attempts >= max_attempts:
        user.mfa_locked_until = now + timedelta(seconds=lock_seconds)
        return True
    return False
