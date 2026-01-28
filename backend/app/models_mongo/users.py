"""
User model for MongoDB using Beanie
"""
from beanie import Document
from pydantic import Field, EmailStr
from typing import Optional
from datetime import datetime
from enum import Enum
from app.utils.datetime_utils import get_current_time


class UserRole(str, Enum):
    """User role enumeration"""
    REGULAR = "regular"
    ADMIN = "admin"


class UserStatus(str, Enum):
    """User status enumeration"""
    PENDING = "pending"      # في انتظار الموافقة
    APPROVED = "approved"    # موافق عليه
    REJECTED = "rejected"    # مرفوض
    ACTIVE = "active"        # نشط (بعد الموافقة)


class User(Document):
    """User model for authentication and authorization"""
    
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    hashed_password: str
    
    # Role and status
    role: UserRole = Field(default=UserRole.REGULAR)
    status: UserStatus = Field(default=UserStatus.PENDING)
    is_active: bool = Field(default=False)  # False until approved
    
    # Approval information
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None  # User ID
    rejection_reason: Optional[str] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=get_current_time)
    last_login: Optional[datetime] = None
    
    class Settings:
        name = "users"  # Collection name
        indexes = [
            "username",
            "email",
            "created_at"
        ]
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role={self.role.value}, status={self.status.value})>"
    
    def is_admin(self) -> bool:
        """Check if user is admin"""
        return self.role == UserRole.ADMIN
    
    def can_login(self) -> bool:
        """Check if user can login (approved and active)"""
        return self.status in [UserStatus.APPROVED, UserStatus.ACTIVE] and self.is_active
