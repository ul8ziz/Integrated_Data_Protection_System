import json
import logging
import sys
import os

# Add the parent directory to sys.path to allow importing app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_db, init_db
from app.models.policies import Policy
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def export_policies(filename="policies.json"):
    """Export all policies to a JSON file"""
    logger.info(f"Exporting policies to {filename}...")
    db = next(get_db())
    try:
        policies = db.query(Policy).all()
        policies_data = []
        for policy in policies:
            policies_data.append({
                "name": policy.name,
                "description": policy.description,
                "entity_types": policy.entity_types,
                "action": policy.action,
                "severity": policy.severity,
                "enabled": policy.enabled,
                "apply_to_network": policy.apply_to_network,
                "apply_to_devices": policy.apply_to_devices,
                "apply_to_storage": policy.apply_to_storage,
                "gdpr_compliant": policy.gdpr_compliant,
                "hipaa_compliant": policy.hipaa_compliant,
                "created_by": policy.created_by
            })
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(policies_data, f, indent=4, ensure_ascii=False)
        
        logger.info(f"Successfully exported {len(policies_data)} policies to {filename}")
    
    except Exception as e:
        logger.error(f"Error exporting policies: {e}")
    finally:
        db.close()

def import_policies(filename="policies.json"):
    """Import policies from a JSON file"""
    logger.info(f"Importing policies from {filename}...")
    db = next(get_db())
    try:
        # Ensure tables exist
        init_db()
        
        with open(filename, "r", encoding="utf-8") as f:
            policies_data = json.load(f)
            
        created_count = 0
        skipped_count = 0
        
        for policy_data in policies_data:
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
            logger.info(f"Created policy: {policy_data['name']}")
        
        db.commit()
        logger.info(f"Import completed: {created_count} new, {skipped_count} skipped")
        
    except FileNotFoundError:
        logger.error(f"File {filename} not found!")
    except Exception as e:
        logger.error(f"Error importing policies: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python migrate_policies.py export  -> To save policies to file")
        print("  python migrate_policies.py import  -> To load policies from file")
        sys.exit(1)
        
    command = sys.argv[1].lower()
    
    if command == "export":
        export_policies()
    elif command == "import":
        import_policies()
    else:
        print(f"Unknown command: {command}")

