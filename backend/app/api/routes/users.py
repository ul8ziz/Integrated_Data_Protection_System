"""
API routes for user management (Admin only)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.models.users import User, UserRole, UserStatus
from app.schemas.users import (
    UserResponse, UserDetailResponse, UserCreate, UserUpdate,
    ApproveUserRequest, RejectUserRequest
)
from app.services.auth_service import get_password_hash
from app.api.dependencies import get_current_admin

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("/", response_model=List[UserDetailResponse])
async def get_users(
    status_filter: Optional[UserStatus] = Query(None, alias="status"),
    role_filter: Optional[UserRole] = Query(None, alias="role"),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Get all users (Admin only)
    
    Query parameters:
    - status: Filter by status (pending, approved, rejected, active)
    - role: Filter by role (regular, admin)
    - search: Search by username or email
    """
    query = db.query(User)
    
    # Apply filters
    if status_filter:
        query = query.filter(User.status == status_filter)
    
    if role_filter:
        query = query.filter(User.role == role_filter)
    
    if search:
        query = query.filter(
            or_(
                User.username.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
        )
    
    users = query.order_by(User.created_at.desc()).all()
    return users


@router.get("/pending", response_model=List[UserDetailResponse])
async def get_pending_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Get all pending users waiting for approval (Admin only)
    """
    pending_users = db.query(User).filter(
        User.status == UserStatus.PENDING
    ).order_by(User.created_at.asc()).all()
    
    return pending_users


@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Get user by ID (Admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.post("/", response_model=UserDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Create a new user (Admin only)
    
    Users created by admin are automatically approved.
    """
    # Check if username exists
    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Check if email exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )
    
    # Create user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        role=user_data.role if hasattr(user_data, 'role') else UserRole.REGULAR,
        status=UserStatus.APPROVED,  # Auto-approved when created by admin
        is_active=True,
        approved_at=datetime.utcnow(),
        approved_by=current_user.id
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@router.put("/{user_id}", response_model=UserDetailResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Update user (Admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields
    if user_data.username is not None:
        # Check if new username is taken
        existing = db.query(User).filter(
            User.username == user_data.username,
            User.id != user_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        user.username = user_data.username
    
    if user_data.email is not None:
        # Check if new email is taken
        existing = db.query(User).filter(
            User.email == user_data.email,
            User.id != user_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        user.email = user_data.email
    
    if user_data.password is not None:
        user.hashed_password = get_password_hash(user_data.password)
    
    if user_data.role is not None:
        user.role = user_data.role
    
    if user_data.status is not None:
        user.status = user_data.status
        # Auto-activate if approved
        if user_data.status in [UserStatus.APPROVED, UserStatus.ACTIVE]:
            user.is_active = True
            if not user.approved_at:
                user.approved_at = datetime.utcnow()
                user.approved_by = current_user.id
        else:
            user.is_active = False
    
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    
    db.commit()
    db.refresh(user)
    
    return user


@router.post("/{user_id}/approve", response_model=UserDetailResponse)
async def approve_user(
    user_id: int,
    request: ApproveUserRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Approve a pending user (Admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.status != UserStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User is not pending. Current status: {user.status.value}"
        )
    
    # Approve user
    user.status = UserStatus.APPROVED
    user.is_active = True
    user.approved_at = datetime.utcnow()
    user.approved_by = current_user.id
    user.rejection_reason = None  # Clear any previous rejection reason
    
    db.commit()
    db.refresh(user)
    
    return user


@router.post("/{user_id}/reject", response_model=UserDetailResponse)
async def reject_user(
    user_id: int,
    request: RejectUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Reject a pending user (Admin only)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.status != UserStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User is not pending. Current status: {user.status.value}"
        )
    
    # Reject user
    user.status = UserStatus.REJECTED
    user.is_active = False
    user.rejection_reason = request.reason
    user.approved_by = current_user.id
    
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Delete a user (Admin only)
    
    Cannot delete yourself.
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    db.delete(user)
    db.commit()
    
    return None


@router.get("/stats/summary")
async def get_user_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Get user statistics (Admin only)
    """
    total_users = db.query(User).count()
    pending_users = db.query(User).filter(User.status == UserStatus.PENDING).count()
    approved_users = db.query(User).filter(User.status == UserStatus.APPROVED).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    admin_users = db.query(User).filter(User.role == UserRole.ADMIN).count()
    regular_users = db.query(User).filter(User.role == UserRole.REGULAR).count()
    
    return {
        "total_users": total_users,
        "pending_users": pending_users,
        "approved_users": approved_users,
        "active_users": active_users,
        "admin_users": admin_users,
        "regular_users": regular_users
    }

