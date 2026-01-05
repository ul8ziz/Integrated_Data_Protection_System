import sys
import os
from datetime import datetime

# Add the current directory to python path
sys.path.append(os.getcwd())

from app.database import engine, SessionLocal, Base
from app.models.users import User, UserRole, UserStatus
from app.services.auth_service import get_password_hash

def create_users():
    db = SessionLocal()
    try:
        # Create tables
        from app.models import users, policies, alerts, logs
        Base.metadata.create_all(bind=engine)
        
        # 1. Admin User
        admin_username = "admin"
        admin_email = "admin@secure.local"
        admin_password = "admin123"

        admin = db.query(User).filter(User.username == admin_username).first()
        if not admin:
            admin = User(
                username=admin_username,
                email=admin_email,
                hashed_password=get_password_hash(admin_password),
                role=UserRole.ADMIN,
                status=UserStatus.ACTIVE,
                is_active=True,
                approved_at=datetime.utcnow()
            )
            db.add(admin)
            print(f"Admin user created: {admin_username} / {admin_password}")
        else:
            admin.status = UserStatus.ACTIVE
            admin.is_active = True
            admin.hashed_password = get_password_hash(admin_password)
            print(f"Admin user updated.")

        # 2. Regular User
        user_username = "user"
        user_email = "user@secure.local"
        user_password = "user123"

        user = db.query(User).filter(User.username == user_username).first()
        if not user:
            user = User(
                username=user_username,
                email=user_email,
                hashed_password=get_password_hash(user_password),
                role=UserRole.REGULAR,
                status=UserStatus.ACTIVE,
                is_active=True,
                approved_at=datetime.utcnow()
            )
            db.add(user)
            print(f"Regular user created: {user_username} / {user_password}")
        else:
            user.status = UserStatus.ACTIVE
            user.is_active = True
            user.hashed_password = get_password_hash(user_password)
            print(f"Regular user updated.")

        db.commit()
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    create_users()
