"""
User model for authentication and authorization
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class UserRole(enum.Enum):
    """User role enumeration"""
    REGULAR = "regular"
    ADMIN = "admin"


class UserStatus(enum.Enum):
    """User status enumeration"""
    PENDING = "pending"      # في انتظار الموافقة
    APPROVED = "approved"    # موافق عليه
    REJECTED = "rejected"    # مرفوض
    ACTIVE = "active"        # نشط (بعد الموافقة)


class User(Base):
    """User model for authentication and authorization"""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    
    # Role and status
    role = Column(Enum(UserRole), nullable=False, default=UserRole.REGULAR)
    status = Column(Enum(UserStatus), nullable=False, default=UserStatus.PENDING)
    is_active = Column(Boolean, default=False)  # False until approved
    
    # Approval information
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    approver = relationship("User", remote_side=[id], foreign_keys=[approved_by])
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role={self.role.value}, status={self.status.value})>"
    
    def is_admin(self) -> bool:
        """Check if user is admin"""
        return self.role == UserRole.ADMIN
    
    def can_login(self) -> bool:
        """Check if user can login (approved and active)"""
        return self.status in [UserStatus.APPROVED, UserStatus.ACTIVE] and self.is_active

