"""
Policy service for managing data protection policies
"""
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.models.policies import Policy
from app.models.alerts import Alert, AlertSeverity, AlertStatus
from app.models.logs import Log, DetectedEntity
from app.services.presidio_service import PresidioService
from app.services.mydlp_service import MyDLPService
from app.services.encryption_service import EncryptionService
import logging

logger = logging.getLogger(__name__)


class PolicyService:
    """Service for managing and applying data protection policies"""
    
    def __init__(self):
        """Initialize policy service"""
        self.presidio = PresidioService()
        self.mydlp = MyDLPService()
        self.encryption = EncryptionService()
    
    def get_active_policies(self, db: Session) -> List[Policy]:
        """
        Get all active policies
        
        Args:
            db: Database session
            
        Returns:
            List of active policies
        """
        return db.query(Policy).filter(Policy.enabled == True).all()
    
    def apply_policy(self, db: Session, text: str, source_ip: str = None, 
                    source_user: str = None, source_device: str = None) -> Dict[str, Any]:
        """
        Apply policies to text and take appropriate actions
        
        Args:
            db: Database session
            text: Text to analyze
            source_ip: Source IP address
            source_user: Source user
            source_device: Source device
            
        Returns:
            Result dictionary with actions taken
        """
        # Analyze text with Presidio
        detected_entities = self.presidio.analyze(text)
        
        if not detected_entities:
            return {
                "sensitive_data_detected": False,
                "actions_taken": [],
                "blocked": False
            }
        
        # Get active policies
        policies = self.get_active_policies(db)
        
        # Check which policies apply
        actions_taken = []
        blocked = False
        alert_created = False
        
        for policy in policies:
            # Check if policy applies to detected entities
            policy_entities = policy.entity_types or []
            relevant_entities = [
                e for e in detected_entities 
                if e["entity_type"] in policy_entities
            ]
            
            if not relevant_entities:
                continue
            
            # Apply policy action
            if policy.action == "block":
                # Block with MyDLP
                if self.mydlp.block_data_transfer(
                    source_ip=source_ip or "unknown",
                    destination="external",
                    detected_entities=relevant_entities,
                    reason=f"Policy violation: {policy.name}"
                ):
                    blocked = True
                    actions_taken.append(f"blocked_by_policy_{policy.id}")
                    
                    # Always create alert for blocked actions
                    self._create_alert(
                        db=db,
                        policy=policy,
                        detected_entities=relevant_entities,
                        source_ip=source_ip,
                        source_user=source_user,
                        source_device=source_device,
                        blocked=True
                    )
                    alert_created = True
            
            elif policy.action == "encrypt":
                # Encrypt detected entities
                for entity in relevant_entities:
                    encrypted_value = self.encryption.encrypt(entity["value"])
                    actions_taken.append(f"encrypted_{entity['entity_type']}")
            
            elif policy.action == "alert":
                # Create alert
                if not alert_created:
                    self._create_alert(
                        db=db,
                        policy=policy,
                        detected_entities=relevant_entities,
                        source_ip=source_ip,
                        source_user=source_user,
                        source_device=source_device,
                        blocked=blocked
                    )
                    alert_created = True
                    actions_taken.append("alert_created")
        
        # Log the event
        self._log_event(
            db=db,
            event_type="policy_applied",
            message=f"Applied policies to text, detected {len(detected_entities)} entities",
            source_ip=source_ip,
            source_user=source_user,
            metadata={
                "detected_entities_count": len(detected_entities),
                "policies_applied": len(policies),
                "blocked": blocked
            }
        )
        
        # Store detected entities
        for entity in detected_entities:
            self._store_detected_entity(
                db=db,
                entity=entity,
                source_text_hash=self.encryption.hash_text(text)
            )
        
        return {
            "sensitive_data_detected": True,
            "detected_entities": detected_entities,
            "actions_taken": actions_taken,
            "blocked": blocked,
            "alert_created": alert_created
        }
    
    def _create_alert(self, db: Session, policy: Policy, detected_entities: List[Dict],
                     source_ip: str = None, source_user: str = None, 
                     source_device: str = None, blocked: bool = False):
        """Create an alert for policy violation"""
        try:
            # Determine severity based on policy
            severity_map = {
                "low": AlertSeverity.LOW,
                "medium": AlertSeverity.MEDIUM,
                "high": AlertSeverity.HIGH,
                "critical": AlertSeverity.CRITICAL
            }
            severity = severity_map.get(policy.severity, AlertSeverity.MEDIUM)
            
            alert = Alert(
                title=f"Sensitive data detected - Policy: {policy.name}",
                description=f"Detected {len(detected_entities)} sensitive entities",
                severity=severity,
                status=AlertStatus.PENDING,
                source_ip=source_ip,
                source_user=source_user,
                source_device=source_device,
                detected_entities=detected_entities,
                policy_id=policy.id,
                action_taken=policy.action,
                blocked=blocked
            )
            
            db.add(alert)
            db.commit()
            logger.info(f"Alert created: {alert.id}")
            
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            db.rollback()
    
    def _log_event(self, db: Session, event_type: str, message: str,
                   source_ip: str = None, source_user: str = None, metadata: Dict = None):
        """Log an event"""
        try:
            log = Log(
                event_type=event_type,
                message=message,
                level="INFO",
                source_ip=source_ip,
                source_user=source_user,
                extra_data=metadata or {}
            )
            db.add(log)
            db.commit()
            
        except Exception as e:
            logger.error(f"Error logging event: {e}")
            db.rollback()
    
    def _store_detected_entity(self, db: Session, entity: Dict, source_text_hash: str):
        """Store detected entity in database"""
        try:
            # Encrypt the value before storing
            encrypted_value = self.encryption.encrypt(entity["value"])
            
            detected_entity = DetectedEntity(
                entity_type=entity["entity_type"],
                value=encrypted_value,
                confidence=entity["score"],
                start_position=entity["start"],
                end_position=entity["end"],
                source_text_hash=source_text_hash,
                action="encrypted"
            )
            
            db.add(detected_entity)
            db.commit()
            
        except Exception as e:
            logger.error(f"Error storing detected entity: {e}")
            db.rollback()

