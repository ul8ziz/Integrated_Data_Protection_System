"""
Email monitoring service for detecting and blocking sensitive data in emails
"""
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.services.presidio_service import PresidioService
from app.services.policy_service import PolicyService
from app.services.mydlp_service import MyDLPService
from app.models.logs import Log, DetectedEntity
from app.models.alerts import Alert, AlertSeverity, AlertStatus
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailMonitoringService:
    """Service for monitoring and analyzing emails for sensitive data"""
    
    def __init__(self):
        """Initialize email monitoring service"""
        self.presidio = PresidioService()
        self.policy_service = PolicyService()
        self.mydlp = MyDLPService()
    
    def analyze_email(self, db: Session, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze email content for sensitive data
        
        Args:
            db: Database session
            email_data: Email information containing:
                - from: Sender email address
                - to: List of recipient email addresses
                - subject: Email subject
                - body: Email body text
                - attachments: List of attachment filenames (optional)
                - source_ip: Source IP address (optional, defaults to 127.0.0.1)
                - source_user: Source user (optional)
        
        Returns:
            Analysis result with detected entities and actions taken
        """
        try:
            # Extract email content
            from_email = email_data.get("from", "unknown@localhost")
            to_emails = email_data.get("to", [])
            subject = email_data.get("subject", "")
            body = email_data.get("body", "")
            attachments = email_data.get("attachments", [])
            source_ip = email_data.get("source_ip", "127.0.0.1")
            source_user = email_data.get("source_user", from_email)
            
            # Combine subject and body for analysis
            full_text = f"{subject}\n\n{body}"
            
            # Analyze with Presidio
            detected_entities = self.presidio.analyze(full_text)
            
            # Log email received
            self._log_email_event(
                db=db,
                event_type="email_received",
                message=f"Email from {from_email} to {', '.join(to_emails)}",
                source_ip=source_ip,
                source_user=source_user,
                email_data={
                    "from": from_email,
                    "to": to_emails,
                    "subject": subject,
                    "has_attachments": len(attachments) > 0,
                    "attachment_count": len(attachments)
                }
            )
            
            if not detected_entities:
                return {
                    "sensitive_data_detected": False,
                    "detected_entities": [],
                    "action": "allow",
                    "blocked": False,
                    "message": "No sensitive data detected"
                }
            
            # Apply policies
            policy_result = self.policy_service.apply_policy(
                db=db,
                text=full_text,
                source_ip=source_ip,
                source_user=source_user,
                source_device="email_client"
            )
            
            # Determine action
            action = "block" if policy_result.get("blocked", False) else "alert" if policy_result.get("alert_created", False) else "allow"
            
            # If blocked, notify MyDLP
            if action == "block":
                self.mydlp.block_email(
                    email_id=f"{from_email}_{datetime.now().isoformat()}",
                    reason=f"Policy violation: {len(detected_entities)} sensitive entities detected"
                )
                
                # Create alert
                self._create_email_alert(
                    db=db,
                    from_email=from_email,
                    to_emails=to_emails,
                    subject=subject,
                    detected_entities=detected_entities,
                    source_ip=source_ip,
                    source_user=source_user,
                    blocked=True
                )
            
            # Store detected entities
            for entity in detected_entities:
                self._store_detected_entity(
                    db=db,
                    entity=entity,
                    source_text_hash=self.policy_service.encryption.hash_text(full_text),
                    source_file=f"email_{from_email}_{datetime.now().timestamp()}"
                )
            
            return {
                "sensitive_data_detected": True,
                "detected_entities": detected_entities,
                "action": action,
                "blocked": action == "block",
                "alert_created": policy_result.get("alert_created", False),
                "message": f"Email {'blocked' if action == 'block' else 'allowed'} - {len(detected_entities)} entities detected"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing email: {e}")
            return {
                "sensitive_data_detected": False,
                "error": str(e),
                "action": "allow",
                "blocked": False
            }
    
    def _log_email_event(self, db: Session, event_type: str, message: str,
                         source_ip: str = None, source_user: str = None,
                         email_data: Dict = None):
        """Log email event"""
        try:
            log = Log(
                event_type=event_type,
                message=message,
                level="INFO",
                source_ip=source_ip or "127.0.0.1",
                source_user=source_user,
                extra_data=email_data or {}
            )
            db.add(log)
            db.commit()
        except Exception as e:
            logger.error(f"Error logging email event: {e}")
            db.rollback()
    
    def _create_email_alert(self, db: Session, from_email: str, to_emails: List[str],
                           subject: str, detected_entities: List[Dict],
                           source_ip: str = None, source_user: str = None,
                           blocked: bool = False):
        """Create alert for email violation"""
        try:
            # Determine severity based on number of entities
            if len(detected_entities) >= 5:
                severity = AlertSeverity.CRITICAL
            elif len(detected_entities) >= 3:
                severity = AlertSeverity.HIGH
            elif len(detected_entities) >= 1:
                severity = AlertSeverity.MEDIUM
            else:
                severity = AlertSeverity.LOW
            
            alert = Alert(
                title=f"Email blocked: Sensitive data detected",
                description=f"Email from {from_email} to {', '.join(to_emails)} contained {len(detected_entities)} sensitive entities",
                severity=severity,
                status=AlertStatus.PENDING,
                source_ip=source_ip or "127.0.0.1",
                source_user=source_user or from_email,
                policy_id=None,
                blocked=blocked
            )
            
            db.add(alert)
            db.commit()
            logger.info(f"Email alert created: {alert.id}")
            
        except Exception as e:
            logger.error(f"Error creating email alert: {e}")
            db.rollback()
    
    def _store_detected_entity(self, db: Session, entity: Dict, source_text_hash: str,
                              source_file: str = None):
        """Store detected entity in database"""
        try:
            # Encrypt the value before storing
            encrypted_value = self.policy_service.encryption.encrypt(entity["value"])
            
            detected_entity = DetectedEntity(
                entity_type=entity["entity_type"],
                value=encrypted_value,
                confidence=entity["score"],
                start_position=entity["start"],
                end_position=entity["end"],
                source_text_hash=source_text_hash,
                source_file=source_file,
                action="detected"
            )
            
            db.add(detected_entity)
            db.commit()
            
        except Exception as e:
            logger.error(f"Error storing detected entity: {e}")
            db.rollback()
    
    def get_email_statistics(self, db: Session, days: int = 7) -> Dict[str, Any]:
        """
        Get email monitoring statistics
        
        Args:
            db: Database session
            days: Number of days to look back
            
        Returns:
            Statistics dictionary
        """
        try:
            from datetime import timedelta
            start_date = datetime.now() - timedelta(days=days)
            
            # Count email events
            email_logs = db.query(Log).filter(
                Log.event_type == "email_received",
                Log.created_at >= start_date
            ).count()
            
            # Count blocked emails
            blocked_alerts = db.query(Alert).filter(
                Alert.created_at >= start_date,
                Alert.blocked == True,
                Alert.title.like("Email blocked%")
            ).count()
            
            # Count detected entities in emails
            email_entities = db.query(DetectedEntity).filter(
                DetectedEntity.created_at >= start_date,
                DetectedEntity.source_file.like("email_%")
            ).count()
            
            return {
                "period_days": days,
                "total_emails_analyzed": email_logs,
                "blocked_emails": blocked_alerts,
                "detected_entities": email_entities,
                "allowed_emails": email_logs - blocked_alerts
            }
            
        except Exception as e:
            logger.error(f"Error getting email statistics: {e}")
            return {
                "period_days": days,
                "total_emails_analyzed": 0,
                "blocked_emails": 0,
                "detected_entities": 0,
                "allowed_emails": 0
            }

