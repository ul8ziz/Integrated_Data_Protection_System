"""
API routes for authentication - MongoDB version
"""
from fastapi import APIRouter, Depends, HTTPException, status
import logging
import base64
import io
from typing import Optional, Union

import qrcode

from app.config import settings
from app.utils.datetime_utils import get_current_time
from app.models_mongo.users import User, UserRole, UserStatus
from app.models_mongo.departments import Department
from app.schemas.users import (
    LoginRequest,
    TokenResponse,
    UserRegister,
    UserResponse,
    MFARequiredResponse,
    MFAVerifyRequest,
    MFASetupStartResponse,
    MFASetupConfirmRequest,
    MFADisableRequest,
)
from app.services.auth_service import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_mfa_pending_token,
    decode_access_token,
    JWT_TYPE_MFA_PENDING,
)
from app.services.login_lockout import (
    clear_expired_lock,
    record_failed_password,
    reset_lockout_on_success,
    retry_after_seconds,
)
from app.services.mfa_lockout import (
    clear_expired_mfa_lock,
    record_failed_mfa,
    reset_mfa_lockout_on_success,
    mfa_retry_after_seconds,
)
from app.services.totp_service import (
    random_base32_secret,
    provisioning_uri,
    verify_totp_code,
)
from app.utils.totp_secret_crypto import encrypt_totp_secret, decrypt_totp_secret
from app.api.dependencies import get_current_user
from app.utils.validators import sanitize_input, encode_special_chars

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def _access_token_for_user(user: User) -> str:
    return create_access_token(
        {
            "sub": user.username,
            "user_id": str(user.id),
            "role": user.role.value,
        }
    )


async def _department_name_for_user(user: User) -> Optional[str]:
    if not getattr(user, "department_id", None):
        return None
    try:
        dept = await Department.get(user.department_id)
        return dept.name if dept else None
    except Exception:
        return None


async def build_user_response(user: User) -> UserResponse:
    department_name = await _department_name_for_user(user)
    return UserResponse(
        id=str(user.id) if user.id is not None else "",
        username=user.username,
        email=user.email,
        role=user.role,
        status=user.status,
        is_active=user.is_active,
        created_at=user.created_at,
        approved_at=user.approved_at,
        last_login=user.last_login,
        approved_by=str(user.approved_by) if user.approved_by else None,
        rejection_reason=user.rejection_reason,
        department_id=getattr(user, "department_id", None),
        department_name=department_name,
        totp_enabled=bool(getattr(user, "totp_enabled", False)),
    )


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
    
    # Validate department exists
    try:
        department = await Department.get(user_data.department_id)
        if not department:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid department"
            )
        department_name = department.name
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid department"
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
        is_active=False,  # Will be activated after approval
        department_id=user_data.department_id
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
        rejection_reason=new_user.rejection_reason,
        department_id=new_user.department_id,
        department_name=department_name,
        totp_enabled=False,
    )


@router.post("/login", response_model=Union[TokenResponse, MFARequiredResponse])
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
        
        now = get_current_time()
        if clear_expired_lock(user, now):
            await user.save()

        if user.is_login_locked(now):
            secs = retry_after_seconds(user, now)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many failed login attempts. Try again in {secs} second(s).",
                headers={"Retry-After": str(secs)},
            )

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
            just_locked = record_failed_password(user)
            await user.save()
            if just_locked:
                logger.warning(f"Login lockout activated for user: {user.username}")
                secs = retry_after_seconds(user, get_current_time())
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many failed login attempts. Try again in {secs} second(s).",
                    headers={"Retry-After": str(secs)},
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )
        
        logger.info(f"Password verified for user: {user.username}")
        reset_lockout_on_success(user)
        
        # Check if user can login
        if not user.can_login():
            await user.save()
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

        now = get_current_time()
        if getattr(user, "totp_enabled", False):
            if clear_expired_mfa_lock(user, now):
                await user.save()
            if user.is_mfa_locked(now):
                secs = mfa_retry_after_seconds(user, now)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        "Too many failed two-factor verification attempts. "
                        f"Try again in {secs} second(s)."
                    ),
                    headers={"Retry-After": str(secs)},
                )
            try:
                mfa_token, expires_in = create_mfa_pending_token(user.username)
            except Exception as e:
                logger.error(f"Error creating MFA pending token: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error creating MFA token",
                )
            return MFARequiredResponse(
                mfa_required=True,
                mfa_token=mfa_token,
                token_type="mfa_pending",
                expires_in=expires_in,
            )

        user.last_login = get_current_time()
        await user.save()

        try:
            access_token = _access_token_for_user(user)
            user_response = await build_user_response(user)
            return TokenResponse(
                access_token=access_token,
                token_type="bearer",
                user=user_response,
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error building login response: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating login response",
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


@router.post("/mfa/verify", response_model=TokenResponse)
async def mfa_verify(body: MFAVerifyRequest):
    """
    Exchange MFA pending token + TOTP code for a full session (after password login).
    """
    payload = decode_access_token(body.mfa_token)
    if payload is None or payload.get("type") != JWT_TYPE_MFA_PENDING:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired MFA token",
        )
    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA token",
        )

    user = await User.find_one({"username": username})
    if user is None or not user.can_login():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA token",
        )
    if not getattr(user, "totp_enabled", False) or not user.totp_secret_encrypted:
        logger.warning("MFA verify called but TOTP not configured for user")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not enabled for this account",
        )

    now = get_current_time()
    if clear_expired_mfa_lock(user, now):
        await user.save()
    if user.is_mfa_locked(now):
        secs = mfa_retry_after_seconds(user, now)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Too many failed verification attempts. "
                f"Try again in {secs} second(s)."
            ),
            headers={"Retry-After": str(secs)},
        )

    try:
        secret = decrypt_totp_secret(user.totp_secret_encrypted)
    except Exception as e:
        logger.error("Failed to decrypt TOTP secret: %s", type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MFA configuration error",
        )

    if not verify_totp_code(secret, body.code):
        just_locked = record_failed_mfa(user)
        await user.save()
        if just_locked:
            secs = mfa_retry_after_seconds(user, get_current_time())
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    "Too many failed verification attempts. "
                    f"Try again in {secs} second(s)."
                ),
                headers={"Retry-After": str(secs)},
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid verification code",
        )

    reset_mfa_lockout_on_success(user)
    user.last_login = get_current_time()
    await user.save()

    return TokenResponse(
        access_token=_access_token_for_user(user),
        token_type="bearer",
        user=await build_user_response(user),
    )


@router.post("/mfa/setup/start", response_model=MFASetupStartResponse)
async def mfa_setup_start(current_user: User = Depends(get_current_user)):
    """
    Begin TOTP enrollment: returns otpauth URI, secret for manual entry, and QR PNG (base64).
    """
    if getattr(current_user, "totp_enabled", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is already enabled",
        )

    secret = random_base32_secret()
    current_user.totp_pending_secret_encrypted = encrypt_totp_secret(secret)
    await current_user.save()

    issuer = settings.TOTP_ISSUER
    uri = provisioning_uri(secret, current_user.email, issuer)

    qr = qrcode.QRCode(version=1, box_size=4, border=2)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    return MFASetupStartResponse(
        otpauth_uri=uri,
        secret_base32=secret,
        qr_code_png_base64=qr_b64,
    )


@router.post("/mfa/setup/confirm")
async def mfa_setup_confirm(
    body: MFASetupConfirmRequest,
    current_user: User = Depends(get_current_user),
):
    """Confirm pending TOTP enrollment with a code from Google Authenticator."""
    if getattr(current_user, "totp_enabled", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is already enabled",
        )
    pending = current_user.totp_pending_secret_encrypted
    if not pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start setup first (call /api/auth/mfa/setup/start)",
        )
    try:
        secret = decrypt_totp_secret(pending)
    except Exception:
        logger.error("Failed to decrypt pending TOTP secret")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MFA setup error",
        )

    if not verify_totp_code(secret, body.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid verification code",
        )

    current_user.totp_secret_encrypted = pending
    current_user.totp_pending_secret_encrypted = None
    current_user.totp_enabled = True
    await current_user.save()

    return {"message": "Two-factor authentication enabled", "totp_enabled": True}


@router.post("/mfa/disable")
async def mfa_disable(
    body: MFADisableRequest,
    current_user: User = Depends(get_current_user),
):
    """Disable TOTP; requires password and current authenticator code."""
    if not getattr(current_user, "totp_enabled", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not enabled",
        )

    sanitized_password = sanitize_input(body.password)
    if sanitized_password != body.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password contains invalid characters",
        )
    if not verify_password(body.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )

    if not body.code or not str(body.code).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code from your authenticator app is required",
        )

    try:
        secret = decrypt_totp_secret(current_user.totp_secret_encrypted)
    except Exception:
        logger.error("Failed to decrypt TOTP secret for disable")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MFA configuration error",
        )

    if not verify_totp_code(secret, body.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid verification code",
        )

    current_user.totp_enabled = False
    current_user.totp_secret_encrypted = None
    current_user.totp_pending_secret_encrypted = None
    reset_mfa_lockout_on_success(current_user)
    await current_user.save()

    return {"message": "Two-factor authentication disabled", "totp_enabled": False}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user information
    """
    return await build_user_response(current_user)


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user)
):
    """
    Logout (client should discard token)
    """
    return {"message": "Logged out successfully"}
