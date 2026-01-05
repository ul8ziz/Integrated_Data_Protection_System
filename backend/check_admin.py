"""Check admin user status"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal
from app.models.users import User, UserRole, UserStatus
from app.services.auth_service import verify_password

db = SessionLocal()
try:
    admin = db.query(User).filter(User.username == 'admin').first()
    if admin:
        print(f"[OK] User found: {admin.username}")
        print(f"  Email: {admin.email}")
        print(f"  Role: {admin.role.value}")
        print(f"  Status: {admin.status.value}")
        print(f"  Is Active: {admin.is_active}")
        print(f"  Can Login: {admin.can_login()}")
        
        # Test password
        test_password = "admin123"
        password_valid = verify_password(test_password, admin.hashed_password)
        print(f"  Password 'admin123' valid: {password_valid}")
        
        if not admin.can_login():
            print("\n[WARNING] User cannot login. Fixing...")
            admin.status = UserStatus.ACTIVE
            admin.is_active = True
            db.commit()
            print("[OK] User status updated to ACTIVE and is_active=True")
    else:
        print("[ERROR] Admin user not found!")
finally:
    db.close()

