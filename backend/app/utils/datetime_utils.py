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


def format_datetime_server(dt: Optional[datetime]) -> str:
    """
    Format datetime in server timezone for display (e.g. "March 6, 2026 at 02:59 AM")
    
    Args:
        dt: datetime to format (can be None, naive, or timezone-aware)
        
    Returns:
        Formatted string in server timezone, or empty string if dt is None
    """
    if dt is None:
        return ""
    tz = get_timezone()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local_dt = dt.astimezone(tz)
    return local_dt.strftime("%B %d, %Y at %I:%M %p")


def to_iso_utc(dt: Optional[datetime]) -> Optional[str]:
    """
    Serialize datetime to ISO 8601 string with Z (UTC) for API responses.
    Frontend then parses it correctly and converts to user's local time.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    utc_dt = dt.astimezone(timezone.utc)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


# For backward compatibility, use get_current_time() as default
def now() -> datetime:
    """
    Get current datetime (alias for get_current_time)
    
    Returns:
        datetime object with timezone
    """
    return get_current_time()
