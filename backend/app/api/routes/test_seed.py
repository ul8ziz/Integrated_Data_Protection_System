"""
Test-only seed endpoint for E2E tests
ONLY available when ENVIRONMENT=test
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
import os
from app.database import get_db
from app.models.users import User, UserRole, UserStatus
from app.services.auth_service import get_password_hash

router = APIRouter(prefix="/api/test", tags=["Test"])


def check_test_environment():
    """Ensure this endpoint is only available in test environment"""
    env = os.getenv("ENVIRONMENT", "").lower()
    if env != "test":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available in test environment"
        )


@router.post("/seed-users", status_code=status.HTTP_201_CREATED)
async def seed_test_users(db: Session = Depends(get_db)):
    """
    Seed test users for E2E testing
    Creates admin_test and user_test accounts (idempotent)
    ONLY available when ENVIRONMENT=test
    """
    check_test_environment()
    
    test_users = [
        {
            "username": "admin_test",
            "email": "admin_test@example.com",
            "password": "StrongPass123!",
            "role": UserRole.ADMIN,
            "status": UserStatus.ACTIVE,
            "is_active": True
        },
        {
            "username": "user_test",
            "email": "user_test@example.com",
            "password": "StrongPass123!",
            "role": UserRole.REGULAR,
            "status": UserStatus.ACTIVE,
            "is_active": True
        }
    ]
    
    created_users = []
    
    for user_data in test_users:
        # Check if user exists
        existing = db.query(User).filter(
            (User.username == user_data["username"]) | 
            (User.email == user_data["email"])
        ).first()
        
        if existing:
            # Update existing user
            existing.hashed_password = get_password_hash(user_data["password"])
            existing.role = user_data["role"]
            existing.status = user_data["status"]
            existing.is_active = user_data["is_active"]
            existing.approved_at = datetime.utcnow()
            created_users.append({
                "username": existing.username,
                "email": existing.email,
                "role": existing.role.value,
                "status": existing.status.value,
                "action": "updated"
            })
        else:
            # Create new user
            new_user = User(
                username=user_data["username"],
                email=user_data["email"],
                hashed_password=get_password_hash(user_data["password"]),
                role=user_data["role"],
                status=user_data["status"],
                is_active=user_data["is_active"],
                approved_at=datetime.utcnow()
            )
            db.add(new_user)
            created_users.append({
                "username": new_user.username,
                "email": new_user.email,
                "role": new_user.role.value,
                "status": new_user.status.value,
                "action": "created"
            })
    
    db.commit()
    
    return {
        "message": "Test users seeded successfully",
        "users": created_users
    }


@router.delete("/cleanup", status_code=status.HTTP_200_OK)
async def cleanup_test_users(db: Session = Depends(get_db)):
    """
    Cleanup test users (optional, for test isolation)
    ONLY available when ENVIRONMENT=test
    """
    check_test_environment()
    
    test_usernames = ["admin_test", "user_test"]
    deleted_count = 0
    
    for username in test_usernames:
        user = db.query(User).filter(User.username == username).first()
        if user:
            db.delete(user)
            deleted_count += 1
    
    db.commit()
    
    return {
        "message": f"Deleted {deleted_count} test users"
    }

