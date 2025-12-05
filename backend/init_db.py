"""
Initialize database tables and default policies
"""
from app.database import init_db, engine, get_db
from app.models.policies import Policy
from app.models import Alert, Log, DetectedEntity
from sqlalchemy.orm import Session
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
        finally:
            db.close()
        logger.info("Default policies setup completed!")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

