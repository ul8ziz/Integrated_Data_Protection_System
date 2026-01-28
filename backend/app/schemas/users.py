"""
Schemas for user management and authentication
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
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
    password: str = Field(..., min_length=12, max_length=100)
    
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
    pass


class UserUpdate(BaseModel):
    """Schema for updating user"""
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6, max_length=100)
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    is_active: Optional[bool] = None


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


class ApproveUserRequest(BaseModel):
    """Schema for approving a user"""
    pass


class RejectUserRequest(BaseModel):
    """Schema for rejecting a user"""
    reason: Optional[str] = Field(None, description="Reason for rejection")

