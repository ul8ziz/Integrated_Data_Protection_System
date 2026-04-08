"""
Schemas for user management and authentication
"""
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from app.utils.validators import (
    sanitize_input, encode_special_chars, 
    validate_password_strength, validate_email_format
)
try:
    from app.models_mongo.users import UserRole, UserStatus
except ImportError:
    from app.models.users import UserRole, UserStatus


class UserBase(BaseModel):
    """Base user schema"""
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate and sanitize username"""
        if not v:
            raise ValueError("Username is required")
        
        # Sanitize input
        sanitized = sanitize_input(v)
        if sanitized != v:
            raise ValueError("Username contains invalid characters or scripts")
        
        # Encode special characters
        encoded = encode_special_chars(sanitized)
        
        return encoded
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format"""
        is_valid, error_msg = validate_email_format(v)
        if not is_valid:
            raise ValueError(error_msg)
        return v


class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: str = Field(..., min_length=6, max_length=100)
    department_id: Optional[str] = None
    role: Optional[UserRole] = None
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        if not v:
            raise ValueError("Password is required")
        
        # Sanitize input
        sanitized = sanitize_input(v)
        if sanitized != v:
            raise ValueError("Password contains invalid characters or scripts")
        
        # Validate password strength
        is_valid, error_msg = validate_password_strength(sanitized)
        if not is_valid:
            raise ValueError(error_msg)
        
        return sanitized


class UserRegister(UserCreate):
    """Schema for user registration (self-registration)"""
    department_id: str = Field(..., description="Department ID the user belongs to")


class UserUpdate(BaseModel):
    """Schema for updating user"""
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6, max_length=100)
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    is_active: Optional[bool] = None
    department_id: Optional[str] = None


class UserResponse(UserBase):
    """Schema for user response"""
    id: str  # MongoDB uses ObjectId (string)
    role: UserRole
    status: UserStatus
    is_active: bool
    created_at: datetime
    approved_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    approved_by: Optional[str] = None  # MongoDB uses ObjectId (string)
    rejection_reason: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    totp_enabled: bool = False
    
    class Config:
        from_attributes = True


class UserDetailResponse(UserResponse):
    """Detailed user response (for admins)"""
    approved_by: Optional[str] = None  # MongoDB uses ObjectId (string)
    rejection_reason: Optional[str] = None


class LoginRequest(BaseModel):
    """Schema for login request"""
    username: str
    password: str
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate and sanitize username"""
        if not v:
            raise ValueError("Username is required")
        
        # Sanitize input
        sanitized = sanitize_input(v)
        if sanitized != v:
            raise ValueError("Username contains invalid characters or scripts")
        
        return sanitized
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Sanitize password input"""
        if not v:
            raise ValueError("Password is required")
        
        # Sanitize input
        sanitized = sanitize_input(v)
        if sanitized != v:
            raise ValueError("Password contains invalid characters or scripts")
        
        return sanitized


class TokenResponse(BaseModel):
    """Schema for token response"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class MFARequiredResponse(BaseModel):
    """Password OK; user must complete TOTP (Google Authenticator)."""
    mfa_required: bool = True
    mfa_token: str
    token_type: str = "mfa_pending"
    expires_in: int = Field(..., description="Seconds until mfa_token expires")


class MFAVerifyRequest(BaseModel):
    """Complete login after MFA."""
    mfa_token: str = Field(..., min_length=10)
    code: str = Field(..., min_length=6, max_length=8, description="6-digit TOTP from authenticator app")

    @field_validator("code")
    @classmethod
    def digits_only(cls, v: str) -> str:
        s = v.strip().replace(" ", "")
        if not s.isdigit():
            raise ValueError("Code must be numeric")
        if len(s) < 6 or len(s) > 8:
            raise ValueError("Invalid code length")
        return s


class MFASetupStartResponse(BaseModel):
    otpauth_uri: str
    secret_base32: str = Field(..., description="Manual entry in Google Authenticator if QR unavailable")
    qr_code_png_base64: str = Field(..., description="PNG image as base64 (no data: prefix)")


class MFASetupConfirmRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=8)

    @field_validator("code")
    @classmethod
    def digits_only(cls, v: str) -> str:
        s = v.strip().replace(" ", "")
        if not s.isdigit():
            raise ValueError("Code must be numeric")
        return s


class MFADisableRequest(BaseModel):
    password: str = Field(..., min_length=1)
    code: Optional[str] = Field(None, description="Required when TOTP is enabled")

    model_config = ConfigDict(extra="forbid")


class ApproveUserRequest(BaseModel):
    """Schema for approving a user"""
    pass


class RejectUserRequest(BaseModel):
    """Schema for rejecting a user"""
    reason: Optional[str] = Field(None, description="Reason for rejection")


class PolicyAssignmentOption(BaseModel):
    """One policy row for user assignment UI"""
    id: str
    name: str
    enabled: bool
    action: str


class UserPolicyAssignmentsResponse(BaseModel):
    """All policies (non-deleted) and current assignment for a user"""
    user_id: str
    username: str
    policies: List[PolicyAssignmentOption]
    assigned_policy_ids: Optional[List[str]] = None


class UpdateUserPolicyAssignmentsRequest(BaseModel):
    """Replace explicit policy assignment for a user (empty list = no policies)"""
    policy_ids: List[str] = Field(..., description="Policy IDs to apply to this user")
    model_config = ConfigDict(extra="forbid")

