"""
Dependencies for authentication and authorization - MongoDB version
"""
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from app.models_mongo.users import User, UserRole, UserStatus
from app.services.auth_service import decode_access_token

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme)
) -> User:
    """
    Get current authenticated user from JWT token
    
    Raises:
        HTTPException: If token is invalid or user not found
    """
    import logging
    logger = logging.getLogger(__name__)
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode token
        payload = decode_access_token(token)
        if payload is None:
            logger.warning("Token decode failed - invalid token")
            raise credentials_exception
        
        username: str = payload.get("sub")
        if username is None:
            logger.warning("Token payload missing 'sub' field")
            raise credentials_exception
        
        logger.debug(f"Looking up user: {username}")
        
        # Get user from database
        user = await User.find_one({"username": username})
        if user is None:
            logger.warning(f"User not found in database: {username}")
            raise credentials_exception
        
        # Check if user can login
        if not user.can_login():
            logger.warning(f"User cannot login: {username}, status: {user.status.value}, is_active: {user.is_active}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is not approved or active. Please wait for admin approval."
            )
        
        logger.debug(f"User authenticated successfully: {username}")
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_current_user: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise credentials_exception


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user
    
    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active"
        )
    return current_user


async def get_current_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current admin user
    
    Raises:
        HTTPException: If user is not admin
    """
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def get_optional_user(
    request: Request
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None
    Used for endpoints that work with or without authentication
    """
    try:
        # Try to get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            
            payload = decode_access_token(token)
            if payload is None:
                return None
            
            username: str = payload.get("sub")
            if username is None:
                return None
            
            user = await User.find_one({"username": username})
            return user if user and user.can_login() else None
    except Exception:
        # Silently fail if authentication is not available
        pass
    
    return None
