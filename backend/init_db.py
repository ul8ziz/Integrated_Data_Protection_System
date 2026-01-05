"""
Initialize database tables and default policies
"""
from app.database import init_db, engine, get_db
from app.models.policies import Policy
from app.models import Alert, Log, DetectedEntity, User, UserRole, UserStatus
from app.services.auth_service import get_password_hash
from sqlalchemy.orm import Session
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_default_policies(db: Session):
    """Create default data protection policies"""
    
    default_policies = [
        {
            "name": "Block Credit Cards",
            "description": "Automatically block any transmission containing credit card numbers",
            "entity_types": ["CREDIT_CARD"],
            "action": "block",
            "severity": "critical",
            "enabled": True,
            "apply_to_network": True,
            "apply_to_devices": True,
            "apply_to_storage": True,
            "gdpr_compliant": True,
            "hipaa_compliant": True,
            "created_by": "system"
        },
        {
            "name": "Alert on Personal Information",
            "description": "Send alerts when personal information (names, phone numbers, emails) is detected",
            "entity_types": ["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS"],
            "action": "alert",
            "severity": "high",
            "enabled": True,
            "apply_to_network": True,
            "apply_to_devices": True,
            "apply_to_storage": True,
            "gdpr_compliant": True,
            "hipaa_compliant": False,
            "created_by": "system"
        },
        {
            "name": "Block Email Addresses in External Communications",
            "description": "Prevent sending email addresses to external recipients",
            "entity_types": ["EMAIL_ADDRESS"],
            "action": "block",
            "severity": "high",
            "enabled": True,
            "apply_to_network": True,
            "apply_to_devices": False,
            "apply_to_storage": False,
            "gdpr_compliant": True,
            "hipaa_compliant": False,
            "created_by": "system"
        },
        {
            "name": "Alert on Phone Numbers",
            "description": "Monitor and alert when phone numbers are detected in communications",
            "entity_types": ["PHONE_NUMBER"],
            "action": "alert",
            "severity": "medium",
            "enabled": True,
            "apply_to_network": True,
            "apply_to_devices": True,
            "apply_to_storage": True,
            "gdpr_compliant": True,
            "hipaa_compliant": True,
            "created_by": "system"
        },
        {
            "name": "Block Physical Addresses",
            "description": "Prevent transmission of physical addresses to external parties",
            "entity_types": ["ADDRESS"],
            "action": "block",
            "severity": "high",
            "enabled": True,
            "apply_to_network": True,
            "apply_to_devices": True,
            "apply_to_storage": False,
            "gdpr_compliant": True,
            "hipaa_compliant": False,
            "created_by": "system"
        },
        {
            "name": "GDPR Compliance - Block All PII",
            "description": "Comprehensive GDPR compliance policy - blocks all personally identifiable information",
            "entity_types": ["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "ADDRESS", "CREDIT_CARD"],
            "action": "block",
            "severity": "critical",
            "enabled": True,
            "apply_to_network": True,
            "apply_to_devices": True,
            "apply_to_storage": True,
            "gdpr_compliant": True,
            "hipaa_compliant": True,
            "created_by": "system"
        },
        {
            "name": "HIPAA Compliance - Healthcare Data Protection",
            "description": "HIPAA compliance policy for protecting healthcare-related personal information",
            "entity_types": ["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "ADDRESS"],
            "action": "block",
            "severity": "critical",
            "enabled": True,
            "apply_to_network": True,
            "apply_to_devices": True,
            "apply_to_storage": True,
            "gdpr_compliant": False,
            "hipaa_compliant": True,
            "created_by": "system"
        },
        {
            "name": "Monitor Organization Names",
            "description": "Alert when organization names are detected in communications",
            "entity_types": ["ORGANIZATION"],
            "action": "alert",
            "severity": "low",
            "enabled": True,
            "apply_to_network": True,
            "apply_to_devices": False,
            "apply_to_storage": False,
            "gdpr_compliant": False,
            "hipaa_compliant": False,
            "created_by": "system"
        }
    ]
    
    created_count = 0
    skipped_count = 0
    
    for policy_data in default_policies:
        try:
            # Check if policy already exists
            existing = db.query(Policy).filter(Policy.name == policy_data["name"]).first()
            if existing:
                logger.info(f"Policy '{policy_data['name']}' already exists, skipping...")
                skipped_count += 1
                continue
            
            # Create new policy
            policy = Policy(**policy_data)
            db.add(policy)
            created_count += 1
            logger.info(f"Created default policy: {policy_data['name']}")
            
        except Exception as e:
            logger.error(f"Error creating policy '{policy_data['name']}': {e}")
            db.rollback()
            continue
    
    try:
        db.commit()
        logger.info(f"Default policies created: {created_count} new, {skipped_count} already existed")
    except Exception as e:
        logger.error(f"Error committing default policies: {e}")
        db.rollback()


def create_default_admin(db: Session):
    """Create default admin user if it doesn't exist"""
    admin_username = "admin"
    admin_email = "admin@example.com"
    admin_password = "admin123"  # Change this in production!
    
    existing_admin = db.query(User).filter(
        (User.username == admin_username) | (User.email == admin_email)
    ).first()
    
    if existing_admin:
        logger.info(f"Admin user already exists: {admin_username}. Updating password and email...")
        # Update password to ensure it uses the current hashing algorithm
        existing_admin.hashed_password = get_password_hash(admin_password)
        existing_admin.email = admin_email  # Update email to valid format
        existing_admin.role = UserRole.ADMIN
        existing_admin.status = UserStatus.ACTIVE
        existing_admin.is_active = True
        try:
            db.commit()
            logger.info("Admin user password and email updated successfully.")
        except Exception as e:
            logger.error(f"Error updating admin user: {e}")
            db.rollback()
        return
    
    # Create admin user
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
    try:
        db.commit()
        logger.info(f"Default admin user created!")
        logger.info(f"  Username: {admin_username}")
        logger.info(f"  Email: {admin_email}")
        logger.info(f"  Password: {admin_password}")
        logger.warning("⚠️  IMPORTANT: Change the admin password in production!")
    except Exception as e:
        logger.error(f"Error creating admin user: {e}")
        db.rollback()


if __name__ == "__main__":
    logger.info("Initializing database...")
    try:
        init_db()
        logger.info("Database initialized successfully!")
        
        # Create default policies
        logger.info("Creating default policies...")
        db = next(get_db())
        try:
            create_default_policies(db)
            # Create default admin user
            logger.info("Creating default admin user...")
            create_default_admin(db)
        finally:
            db.close()
        logger.info("Default policies and admin user setup completed!")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

