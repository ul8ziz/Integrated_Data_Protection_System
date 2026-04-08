"""
User model for MongoDB using Beanie
"""
from beanie import Document
from pydantic import Field, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum
from app.utils.datetime_utils import get_current_time, ensure_aware_for_compare


class UserRole(str, Enum):
    """User role enumeration"""
    REGULAR = "regular"
    ADMIN = "admin"
    MANAGER = "manager"  # مدير قسم - can manage users in same department only


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

    # Department (for organization structure)
    department_id: Optional[str] = None  # ObjectId of department as string
    
    # Approval information
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None  # User ID
    rejection_reason: Optional[str] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=get_current_time)
    last_login: Optional[datetime] = None
    
    # Login lockout (failed password attempts)
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None

    # TOTP (Google Authenticator) — secrets stored encrypted at rest
    totp_enabled: bool = False
    totp_secret_encrypted: Optional[str] = None
    totp_pending_secret_encrypted: Optional[str] = None
    mfa_failed_attempts: int = 0
    mfa_locked_until: Optional[datetime] = None
    
    # Per-user policy assignment (None = apply all active policies; explicit list = only those IDs)
    assigned_policy_ids: Optional[List[str]] = None
    
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
        """Check if user is admin (مدير نظام)"""
        return self.role == UserRole.ADMIN

    def is_manager(self) -> bool:
        """Check if user can manage users (admin or department manager)"""
        return self.role in (UserRole.ADMIN, UserRole.MANAGER)
    
    def can_login(self) -> bool:
        """Check if user can login (approved and active)"""
        return self.status in [UserStatus.APPROVED, UserStatus.ACTIVE] and self.is_active
    
    def is_login_locked(self, now: datetime) -> bool:
        """True if account is temporarily locked after too many failed password attempts."""
        locked_until = ensure_aware_for_compare(self.locked_until)
        return locked_until is not None and locked_until > now

    def is_mfa_locked(self, now: datetime) -> bool:
        """True if temporarily locked after too many failed MFA code attempts."""
        locked_until = ensure_aware_for_compare(self.mfa_locked_until)
        return locked_until is not None and locked_until > now
