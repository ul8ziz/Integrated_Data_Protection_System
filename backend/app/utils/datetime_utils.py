"""
Datetime utilities with timezone support
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
from app.config import settings

# Try to import pytz, but make it optional
try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False


def get_timezone() -> timezone:
    """
    Get timezone object from settings
    
    Returns:
        timezone object
    """
    if PYTZ_AVAILABLE:
        try:
            # Try to get timezone from pytz
            tz = pytz.timezone(settings.TIMEZONE)
            return tz
        except Exception:
            pass
    
    # Fallback to UTC
    return timezone.utc


def get_current_time() -> datetime:
    """
    Get current datetime with configured timezone
    
    Returns:
        datetime object with timezone
    """
    tz = get_timezone()
    return datetime.now(tz)


def get_utc_time() -> datetime:
    """
    Get current UTC datetime (for compatibility)
    
    Returns:
        datetime object in UTC
    """
    return datetime.now(timezone.utc)


# For backward compatibility, use get_current_time() as default
def now() -> datetime:
    """
    Get current datetime (alias for get_current_time)
    
    Returns:
        datetime object with timezone
    """
    return get_current_time()
