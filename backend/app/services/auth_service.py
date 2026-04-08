"""
Authentication service for user management
"""
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
from app.config import settings
from app.utils.datetime_utils import get_current_time

# Password hashing context
# Use pbkdf2_sha256 as primary (more reliable, no bcrypt version issues)
# bcrypt has compatibility issues with some versions
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# JWT settings
ALGORITHM = "HS256"
# Token expiration time (in hours)
# Default: 24 hours (1 day)
# You can change this to:
# - 1 hour for more security
# - 168 hours (7 days) for convenience
# - 720 hours (30 days) for long sessions
ACCESS_TOKEN_EXPIRE_HOURS = 24

# JWT claim: token purpose (access vs MFA step)
JWT_TYPE_ACCESS = "access"
JWT_TYPE_MFA_PENDING = "mfa_pending"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # Fallback verification for different hash types
        try:
            # Try to verify as pbkdf2_sha256 if default context fails
            from passlib.context import CryptContext
            fallback_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")
            return fallback_context.verify(plain_password, hashed_password)
        except Exception:
            # Fallback to simple hash (only for testing/legacy)
            import hashlib
            return hashlib.sha256(plain_password.encode('utf-8')).hexdigest() == hashed_password


def get_password_hash(password: str) -> str:
    """Hash a password"""
    # Ensure password is not longer than 72 bytes (bcrypt limit)
    if isinstance(password, str):
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            # Truncate to 72 bytes if longer
            password_bytes = password_bytes[:72]
            password = password_bytes.decode('utf-8', errors='ignore')
    
    try:
        # Use pbkdf2_sha256 as fallback if bcrypt fails
        return pwd_context.hash(password)
    except (ValueError, AttributeError) as e:
        # If bcrypt fails (version issue or password too long), use pbkdf2_sha256
        try:
            from passlib.context import CryptContext
            fallback_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
            return fallback_context.hash(password)
        except Exception:
            # Last resort: use simple hash (not secure, but works)
            import hashlib
            return hashlib.sha256(password.encode('utf-8')).hexdigest()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token (full session). Includes iat, type=access, and caller claims (sub, user_id, role).
    """
    to_encode = data.copy()
    if expires_delta:
        expire = get_current_time() + expires_delta
    else:
        expire = get_current_time() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)

    now = get_current_time()
    to_encode.update(
        {
            "exp": expire,
            "iat": int(now.timestamp()),
            "type": JWT_TYPE_ACCESS,
        }
    )
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_mfa_pending_token(username: str) -> tuple[str, int]:
    """
    Short-lived token after password OK, before TOTP verification.
    Returns (jwt, expires_in_seconds).
    """
    minutes = max(1, settings.MFA_PENDING_TOKEN_EXPIRE_MINUTES)
    delta = timedelta(minutes=minutes)
    now = get_current_time()
    expire = now + delta
    to_encode = {
        "sub": username,
        "exp": expire,
        "iat": int(now.timestamp()),
        "type": JWT_TYPE_MFA_PENDING,
    }
    encoded = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded, int(delta.total_seconds())


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode JWT access token
    
    Args:
        token: JWT token to decode
        
    Returns:
        Decoded token data or None if invalid
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

