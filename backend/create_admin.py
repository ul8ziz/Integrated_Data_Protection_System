import sys
import os
from datetime import datetime

# Add the current directory to python path
sys.path.append(os.getcwd())

from app.database import engine, SessionLocal, Base
from app.models.users import User, UserRole, UserStatus
from app.services.auth_service import get_password_hash

def create_admin():
    db = SessionLocal()
    try:
        # Create tables
        from app.models import users, policies, alerts, logs
        Base.metadata.create_all(bind=engine)
        print("Database tables created.")

        admin_username = "admin"
        admin_email = "admin@example.com"
        admin_password = "admin123"

        existing_admin = db.query(User).filter(
            (User.username == admin_username)
        ).first()

        if existing_admin:
            print(f"Admin user '{admin_username}' already exists.")
            # Reset password just in case
            existing_admin.hashed_password = get_password_hash(admin_password)
            existing_admin.status = UserStatus.ACTIVE
            existing_admin.is_active = True
            db.commit()
            print(f"Admin password reset to '{admin_password}'.")
        else:
            admin_user = User(
                username=admin_username,
                email=admin_email,
                hashed_password=get_password_hash(admin_password),
                role=UserRole.ADMIN,
                status=UserStatus.ACTIVE,
                is_active=True,
                approved_at=datetime.utcnow()
            )
            db.add(admin_user)
            db.commit()
            print(f"Admin user created: {admin_username} / {admin_password}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()
