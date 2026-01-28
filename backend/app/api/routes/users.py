"""
API routes for user management (Admin only) - MongoDB version
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional, Dict, Any
from datetime import datetime
from beanie import PydanticObjectId
from app.utils.datetime_utils import get_current_time
from app.models_mongo.users import User, UserRole, UserStatus
from app.schemas.users import (
    UserResponse, UserDetailResponse, UserCreate, UserUpdate,
    ApproveUserRequest, RejectUserRequest
)
from app.services.auth_service import get_password_hash
from app.api.dependencies import get_current_admin

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("/", response_model=Dict[str, Any])
async def get_users(
    status_filter: Optional[UserStatus] = Query(None, alias="status"),
    role_filter: Optional[UserRole] = Query(None, alias="role"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_admin)
):
    """
    Get all users with pagination (Admin only)
    
    Query parameters:
    - status: Filter by status (pending, approved, rejected, active)
    - role: Filter by role (regular, admin)
    - search: Search by username or email
    - page: Page number (default: 1)
    - limit: Items per page (default: 10, max: 100)
    """
    # Handle active users filter specially (needs is_active=True)
    if status_filter:
        status_value = status_filter.value if hasattr(status_filter, 'value') else status_filter
        if status_value == 'active':
            # For active users: (status=approved OR status=active) AND is_active=True
            # Get all users and filter in Python since Beanie doesn't support complex $or easily
            all_users = await User.find({}).sort("-created_at").to_list()
            filtered_users = [
                u for u in all_users
                if u.is_active and (u.status == UserStatus.APPROVED or u.status == UserStatus.ACTIVE)
            ]
            # Apply role filter if provided
            if role_filter:
                role_value = role_filter.value if hasattr(role_filter, 'value') else role_filter
                filtered_users = [u for u in filtered_users if u.role.value == role_value]
            # Apply search filter if provided
            if search:
                search_lower = search.lower()
                filtered_users = [
                    u for u in filtered_users
                    if search_lower in u.username.lower() or search_lower in u.email.lower()
                ]
            # Calculate pagination
            total_count = len(filtered_users)
            skip = (page - 1) * limit
            users_list = filtered_users[skip:skip + limit]
        else:
            # Regular status filter
            query = {"status": status_value}
            if role_filter:
                role_value = role_filter.value if hasattr(role_filter, 'value') else role_filter
                query["role"] = role_value
            base_query = User.find(query)
            # Calculate pagination
            skip = (page - 1) * limit
            # Get total count
            total_count = await base_query.count()
            # Apply search filter if provided (before pagination)
            if search:
                search_lower = search.lower()
                all_users = await base_query.sort("-created_at").to_list()
                filtered_users = [
                    u for u in all_users
                    if search_lower in u.username.lower() or search_lower in u.email.lower()
                ]
                total_count = len(filtered_users)
                users_list = filtered_users[skip:skip + limit]
            else:
                users_list = await base_query.sort("-created_at").skip(skip).limit(limit).to_list()
    else:
        # No status filter
        query = {}
        if role_filter:
            role_value = role_filter.value if hasattr(role_filter, 'value') else role_filter
            query["role"] = role_value
        base_query = User.find(query) if query else User.find({})
        # Calculate pagination
        skip = (page - 1) * limit
        # Get total count
        total_count = await base_query.count()
        # Apply search filter if provided (before pagination)
        if search:
            search_lower = search.lower()
            all_users = await base_query.sort("-created_at").to_list()
            filtered_users = [
                u for u in all_users
                if search_lower in u.username.lower() or search_lower in u.email.lower()
            ]
            total_count = len(filtered_users)
            users_list = filtered_users[skip:skip + limit]
        else:
            users_list = await base_query.sort("-created_at").skip(skip).limit(limit).to_list()
    
    # Convert to response format
    result = []
    for user in users_list:
        result.append(UserDetailResponse(
            id=str(user.id),
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
        ))
    
    # Calculate pagination metadata
    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 0
    
    return {
        "items": result,
        "total": total_count,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }


@router.get("/pending", response_model=List[UserDetailResponse])
async def get_pending_users(
    current_user: User = Depends(get_current_admin)
):
    """
    Get all pending users waiting for approval (Admin only)
    """
    pending_users = await User.find(
        {"status": UserStatus.PENDING.value}
    ).sort("created_at").to_list()
    
    # Convert to response format
    result = []
    for user in pending_users:
        result.append(UserDetailResponse(
            id=str(user.id),
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
        ))
    
    return result


@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_admin)
):
    """
    Get user by ID (Admin only)
    """
    try:
        user = await User.get(user_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserDetailResponse(
        id=str(user.id),
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


@router.post("/", response_model=UserDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_admin)
):
    """
    Create a new user (Admin only)
    
    Users created by admin are automatically approved.
    """
    # Check if username exists
    existing = await User.find_one({"username": user_data.username})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Check if email exists
    existing_email = await User.find_one({"email": user_data.email})
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
        approved_at=get_current_time(),
        approved_by=str(current_user.id)
    )
    
    await new_user.insert()
    
    return UserDetailResponse(
        id=str(new_user.id),
        username=new_user.username,
        email=new_user.email,
        role=new_user.role,
        status=new_user.status,
        is_active=new_user.is_active,
        created_at=new_user.created_at,
        approved_at=new_user.approved_at,
        last_login=new_user.last_login,
        approved_by=new_user.approved_by,
        rejection_reason=new_user.rejection_reason
    )


@router.put("/{user_id}", response_model=UserDetailResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_admin)
):
    """
    Update user (Admin only)
    """
    try:
        user = await User.get(user_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields
    if user_data.username is not None:
        # Check if new username is taken
        existing = await User.find_one({"username": user_data.username})
        if existing and str(existing.id) != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        user.username = user_data.username
    
    if user_data.email is not None:
        # Check if new email is taken
        existing = await User.find_one({"email": user_data.email})
        if existing and str(existing.id) != user_id:
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
                user.approved_at = get_current_time()
                user.approved_by = str(current_user.id)
        else:
            user.is_active = False
    
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    
    await user.save()
    
    return UserDetailResponse(
        id=str(user.id),
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


@router.post("/{user_id}/approve", response_model=UserDetailResponse)
async def approve_user(
    user_id: str,
    request: ApproveUserRequest = None,
    current_user: User = Depends(get_current_admin)
):
    """
    Approve a pending user (Admin only)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Approving user {user_id} by admin {current_user.username}")
        user = await User.get(user_id)
    except Exception as e:
        logger.error(f"User not found: {user_id}, error: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.status != UserStatus.PENDING:
        logger.warning(f"User {user_id} is not pending. Current status: {user.status.value}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User is not pending. Current status: {user.status.value}"
        )
    
    # Approve user
    user.status = UserStatus.APPROVED
    user.is_active = True
    user.approved_at = get_current_time()
    user.approved_by = str(current_user.id)
    user.rejection_reason = None  # Clear any previous rejection reason
    
    await user.save()
    logger.info(f"User {user_id} approved successfully by {current_user.username}")
    
    return UserDetailResponse(
        id=str(user.id),
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


@router.post("/{user_id}/reject", response_model=UserDetailResponse)
async def reject_user(
    user_id: str,
    request: RejectUserRequest,
    current_user: User = Depends(get_current_admin)
):
    """
    Reject a pending user (Admin only)
    """
    try:
        user = await User.get(user_id)
    except Exception:
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
    user.approved_by = str(current_user.id)
    
    await user.save()
    
    return UserDetailResponse(
        id=str(user.id),
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


@router.post("/{user_id}/suspend", response_model=UserDetailResponse)
async def suspend_user(
    user_id: str,
    current_user: User = Depends(get_current_admin)
):
    """
    Suspend (deactivate) a user (Admin only)
    
    Suspended users cannot login but their account is not deleted.
    Cannot suspend yourself.
    """
    if str(user_id) == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot suspend your own account"
        )
    
    try:
        user = await User.get(user_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Suspend user
    user.is_active = False
    await user.save()
    
    return UserDetailResponse(
        id=str(user.id),
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


@router.post("/{user_id}/activate", response_model=UserDetailResponse)
async def activate_user(
    user_id: str,
    current_user: User = Depends(get_current_admin)
):
    """
    Activate a suspended user (Admin only)
    
    Activates a previously suspended user, allowing them to login again.
    """
    try:
        user = await User.get(user_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if user is approved
    if user.status not in [UserStatus.APPROVED, UserStatus.ACTIVE]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot activate user with status: {user.status.value}. User must be approved first."
        )
    
    # Activate user
    user.is_active = True
    if user.status == UserStatus.APPROVED:
        user.status = UserStatus.ACTIVE
    await user.save()
    
    return UserDetailResponse(
        id=str(user.id),
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


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_admin)
):
    """
    Permanently delete a user (Admin only)
    
    Cannot delete yourself.
    WARNING: This action cannot be undone!
    """
    if str(user_id) == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    try:
        user = await User.get(user_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    await user.delete()
    
    return None


@router.get("/stats/summary")
async def get_user_stats(
    current_user: User = Depends(get_current_admin)
):
    """
    Get user statistics (Admin only)
    """
    total_users = await User.find({}).count()
    pending_users = await User.find({"status": UserStatus.PENDING.value}).count()
    approved_users = await User.find({"status": UserStatus.APPROVED.value}).count()
    active_users = await User.find({"is_active": True}).count()
    admin_users = await User.find({"role": UserRole.ADMIN.value}).count()
    regular_users = await User.find({"role": UserRole.REGULAR.value}).count()
    
    return {
        "total_users": total_users,
        "pending_users": pending_users,
        "approved_users": approved_users,
        "active_users": active_users,
        "admin_users": admin_users,
        "regular_users": regular_users
    }
