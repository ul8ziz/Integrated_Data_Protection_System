"""
API routes for authentication
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
import logging
from app.database import get_db
from app.models.users import User, UserRole, UserStatus
from app.schemas.users import (
    LoginRequest, TokenResponse, UserRegister, UserResponse
)
from app.services.auth_service import (
    verify_password, get_password_hash, create_access_token
)
from app.api.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new user account
    
    The account will be created with status "pending" and will require
    admin approval before the user can login.
    """
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        role=UserRole.REGULAR,
        status=UserStatus.PENDING,
        is_active=False  # Will be activated after approval
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login and get access token
    
    Only approved and active users can login.
    """
    logger.info(f"Login attempt for username: {login_data.username}")
    try:
        # Find user by username or email
        user = db.query(User).filter(
            (User.username == login_data.username) | 
            (User.email == login_data.username)
        ).first()
        
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
        user.last_login = datetime.utcnow()
        db.commit()
        
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
                id=user.id,
                username=user.username,
                email=user.email,
                role=user.role,
                status=user.status,
                is_active=user.is_active,
                created_at=user.created_at,
                approved_at=user.approved_at,
                last_login=user.last_login,
                approved_by=user.approved_by,
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
    return current_user


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user)
):
    """
    Logout (client should discard token)
    """
    return {"message": "Logged out successfully"}

