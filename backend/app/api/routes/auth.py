"""
API routes for authentication - MongoDB version
"""
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
import logging
from app.utils.datetime_utils import get_current_time
from app.models_mongo.users import User, UserRole, UserStatus
from app.schemas.users import (
    LoginRequest, TokenResponse, UserRegister, UserResponse
)
from app.services.auth_service import (
    verify_password, get_password_hash, create_access_token
)
from app.api.dependencies import get_current_user
from app.utils.validators import sanitize_input, encode_special_chars

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister
):
    """
    Register a new user account
    
    The account will be created with status "pending" and will require
    admin approval before the user can login.
    
    Inputs are automatically sanitized to prevent script injection.
    """
    # Additional sanitization (schemas already validate, but double-check for security)
    sanitized_username = sanitize_input(user_data.username)
    sanitized_email = sanitize_input(user_data.email)
    sanitized_password = sanitize_input(user_data.password)
    
    # Check if sanitization removed dangerous content
    if sanitized_username != user_data.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username contains invalid characters or scripts"
        )
    
    if sanitized_email != user_data.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email contains invalid characters or scripts"
        )
    
    if sanitized_password != user_data.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password contains invalid characters or scripts"
        )
    
    # Encode special characters
    encoded_username = encode_special_chars(sanitized_username)
    
    # Check if username already exists
    existing_user = await User.find_one({"username": encoded_username})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    existing_email = await User.find_one({"email": sanitized_email})
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(sanitized_password)
    new_user = User(
        username=encoded_username,
        email=sanitized_email,
        hashed_password=hashed_password,
        role=UserRole.REGULAR,
        status=UserStatus.PENDING,
        is_active=False  # Will be activated after approval
    )
    
    await new_user.insert()
    
    return UserResponse(
        id=str(new_user.id),
        username=new_user.username,
        email=new_user.email,
        role=new_user.role,
        status=new_user.status,
        is_active=new_user.is_active,
        created_at=new_user.created_at,
        approved_at=new_user.approved_at,
        last_login=new_user.last_login,
        approved_by=str(new_user.approved_by) if new_user.approved_by else None,
        rejection_reason=new_user.rejection_reason
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest
):
    """
    Login and get access token
    
    Only approved and active users can login.
    Inputs are automatically sanitized to prevent script injection.
    """
    # Additional sanitization (schemas already validate, but double-check for security)
    sanitized_username = sanitize_input(login_data.username)
    sanitized_password = sanitize_input(login_data.password)
    
    # Check if sanitization removed dangerous content
    if sanitized_username != login_data.username:
        logger.warning(f"Login attempt with dangerous username content: {login_data.username[:20]}...")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username contains invalid characters or scripts"
        )
    
    if sanitized_password != login_data.password:
        logger.warning(f"Login attempt with dangerous password content")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password contains invalid characters or scripts"
        )
    
    # Encode special characters for username lookup
    encoded_username = encode_special_chars(sanitized_username)
    
    logger.info(f"Login attempt for username: {encoded_username}")
    try:
        # Find user by username or email
        user = await User.find_one({"username": encoded_username})
        if not user:
            user = await User.find_one({"email": sanitized_username})
        
        logger.info(f"User found: {user is not None}")
        
        if not user:
            logger.warning(f"User not found: {login_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )
        
        logger.info(f"User found: {user.username}, status: {user.status.value}, is_active: {user.is_active}")
        
        # Verify password
        try:
            password_valid = verify_password(login_data.password, user.hashed_password)
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error verifying password"
            )
        
        if not password_valid:
            logger.warning(f"Invalid password for user: {user.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )
        
        logger.info(f"Password verified for user: {user.username}")
        
        # Check if user can login
        if not user.can_login():
            logger.warning(f"User cannot login: {user.username}, status: {user.status.value}, is_active: {user.is_active}")
            if user.status == UserStatus.PENDING:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Your account is pending approval. Please wait for admin approval."
                )
            elif user.status == UserStatus.REJECTED:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Your account has been rejected. Reason: {user.rejection_reason or 'No reason provided'}"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Your account is not active. Please contact administrator."
                )
        
        logger.info(f"User can login: {user.username}")
        
        # Update last login
        user.last_login = get_current_time()
        await user.save()
        
        # Create access token
        try:
            access_token = create_access_token(data={"sub": user.username})
        except Exception as e:
            logger.error(f"Error creating access token: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating access token"
            )
        
        # Create user response
        try:
            user_response = UserResponse(
                id=str(user.id) if hasattr(user.id, '__str__') else user.id,
                username=user.username,
                email=user.email,
                role=user.role,
                status=user.status,
                is_active=user.is_active,
                created_at=user.created_at,
                approved_at=user.approved_at,
                last_login=user.last_login,
                approved_by=str(user.approved_by) if user.approved_by else None,
                rejection_reason=user.rejection_reason
            )
        except Exception as e:
            logger.error(f"Error creating UserResponse: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating user response: {str(e)}"
            )
        
        # Create token response
        try:
            return TokenResponse(
                access_token=access_token,
                token_type="bearer",
                user=user_response
            )
        except Exception as e:
            logger.error(f"Error creating TokenResponse: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating response: {str(e)}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in login: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user information
    """
    return UserResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        status=current_user.status,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        approved_at=current_user.approved_at,
        last_login=current_user.last_login,
        approved_by=str(current_user.approved_by) if current_user.approved_by else None,
        rejection_reason=current_user.rejection_reason
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user)
):
    """
    Logout (client should discard token)
    """
    return {"message": "Logged out successfully"}
