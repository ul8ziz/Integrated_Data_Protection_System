"""
Policy service for managing data protection policies - MongoDB version
"""
from typing import List, Optional, Dict, Any
from app.models_mongo.policies import Policy
from app.models_mongo.alerts import Alert, AlertSeverity, AlertStatus
from app.models_mongo.logs import Log, DetectedEntity
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
    
    async def get_active_policies(self) -> List[Policy]:
        """
        Get all active policies (enabled and not deleted)
        
        Returns:
            List of active policies
        """
        return await Policy.find({"enabled": True, "is_deleted": False}).to_list()
    
    async def apply_policy(self, text: str, source_ip: str = None, 
                    source_user: str = None, source_device: str = None) -> Dict[str, Any]:
        """
        Apply policies to text and take appropriate actions
        
        Args:
            text: Text to analyze
            source_ip: Source IP address
            source_user: Source user
            source_device: Source device
            
        Returns:
            Result dictionary with actions taken
        """
        # Analyze text with Presidio
        detected_entities = self.presidio.analyze(text)
        
        return await self.apply_policy_with_entities(
            detected_entities=detected_entities,
            text=text,
            source_ip=source_ip,
            source_user=source_user,
            source_device=source_device
        )
    
    async def apply_policy_with_entities(self, detected_entities: List[Dict], 
                                   text: str = None, source_ip: str = None, 
                                   source_user: str = None, source_device: str = None) -> Dict[str, Any]:
        """
        Apply policies using pre-detected entities (avoids re-analysis)
        
        Args:
            detected_entities: Pre-detected entities from Presidio
            text: Original text (optional, for logging)
            source_ip: Source IP address
            source_user: Source user
            source_device: Source device
            
        Returns:
            Result dictionary with actions taken
        """
        if not detected_entities:
            return {
                "sensitive_data_detected": False,
                "actions_taken": [],
                "blocked": False,
                "alert_created": False
            }
        
        # Get active policies (enabled and not deleted)
        policies = await self.get_active_policies()
        
        # If no active policies exist, return early - no actions should be taken
        if not policies:
            logger.debug("No active policies found - no actions will be taken")
            logger.info(f"Detected {len(detected_entities)} entities but no active policies available")
            return {
                "sensitive_data_detected": len(detected_entities) > 0,
                "detected_entities": detected_entities,
                "actions_taken": [],
                "blocked": False,
                "alert_created": False,
                "policies_matched": False,
                "applied_policies": [],
                "encrypted_text": None
            }
        
        # Check which policies apply
        actions_taken = []
        blocked = False
        alert_created = False
        matching_policies = []  # Track policies that actually match
        
        for policy in policies:
            # Check if policy applies to detected entities
            policy_entities = policy.entity_types or []
            relevant_entities = [
                e for e in detected_entities 
                if e["entity_type"] in policy_entities
            ]
            
            if not relevant_entities:
                logger.debug(f"Policy {policy.id} ({policy.name}, action={policy.action}) does not apply - no matching entities. Policy entities: {policy_entities}, Detected entities: {[e['entity_type'] for e in detected_entities]}")
                continue
            
            # Policy matches - add to matching policies
            matching_policies.append(policy)
            logger.info(f"Policy {policy.id} ({policy.name}, action={policy.action}) applies - {len(relevant_entities)} relevant entities of types: {[e['entity_type'] for e in relevant_entities]}")
            
            # Apply policy action
            if policy.action == "block":
                logger.info(f"Applying block action for policy {policy.id} ({policy.name})")
                # Block with MyDLP (returns True even if MyDLP is disabled - simulation mode)
                block_result = self.mydlp.block_data_transfer(
                    source_ip=source_ip or "unknown",
                    destination="external",
                    detected_entities=relevant_entities,
                    reason=f"Policy violation: {policy.name}"
                )
                logger.info(f"block_data_transfer returned: {block_result}")
                
                if block_result:
                    blocked = True
                    actions_taken.append(f"blocked_by_policy_{policy.id}")
                    logger.info(f"Email blocked by policy {policy.id} ({policy.name})")
                    
                    # Always create alert for blocked actions
                    await self._create_alert(
                        policy=policy,
                        detected_entities=relevant_entities,
                        source_ip=source_ip,
                        source_user=source_user,
                        source_device=source_device,
                        blocked=True
                    )
                    alert_created = True
                else:
                    logger.warning(f"block_data_transfer returned False for policy {policy.id}")
            
            elif policy.action == "encrypt":
                # Encrypt detected entities in the text
                logger.info(f"Applying encrypt action for policy {policy.id} ({policy.name})")
                for entity in relevant_entities:
                    encrypted_value = self.encryption.encrypt(entity["value"])
                    # Store encrypted value for later text replacement
                    entity["encrypted_value"] = encrypted_value
                    entity["original_value"] = entity["value"]  # Keep original for reference
                    actions_taken.append(f"encrypted_{entity['entity_type']}")
                logger.info(f"Encrypted {len(relevant_entities)} entities for policy {policy.id}")
            
            elif policy.action == "alert":
                # Create alert
                if not alert_created:
                    await self._create_alert(
                        policy=policy,
                        detected_entities=relevant_entities,
                        source_ip=source_ip,
                        source_user=source_user,
                        source_device=source_device,
                        blocked=blocked
                    )
                    alert_created = True
                    actions_taken.append("alert_created")
        
        # Only log and store entities if at least one policy matched
        if matching_policies:
            # Log the event
            if text:
                await self._log_event(
                    event_type="policy_applied",
                    message=f"Applied {len(matching_policies)} matching policies, detected {len(detected_entities)} entities",
                    source_ip=source_ip,
                    source_user=source_user,
                    metadata={
                        "detected_entities_count": len(detected_entities),
                        "policies_applied": len(matching_policies),
                        "matching_policy_ids": [str(p.id) for p in matching_policies],
                        "blocked": blocked
                    }
                )
                
                # Store detected entities only if policies matched
                for entity in detected_entities:
                    await self._store_detected_entity(
                        entity=entity,
                        source_text_hash=self.encryption.hash_text(text)
                    )
        else:
            # No policies matched - log but don't take any action
            logger.info(f"Detected {len(detected_entities)} entities but no matching policies found - no actions taken")
            if text:
                await self._log_event(
                    event_type="entities_detected_no_policy_match",
                    message=f"Detected {len(detected_entities)} entities but no matching policies",
                    source_ip=source_ip,
                    source_user=source_user,
                    metadata={
                        "detected_entities_count": len(detected_entities),
                        "detected_entity_types": list(set([e.get("entity_type", "unknown") for e in detected_entities])),
                        "policies_applied": 0,
                        "blocked": False
                    }
                )
        
        # Apply encryption to text if encrypt policies were applied
        encrypted_text = None
        if text and any(p.action == "encrypt" for p in matching_policies):
            encrypted_text = text
            # Sort entities by start position (descending) to replace from end to start
            # This prevents position shifts when replacing
            entities_to_encrypt = []
            for policy in matching_policies:
                if policy.action == "encrypt":
                    policy_entities = policy.entity_types or []
                    for entity in detected_entities:
                        if (entity["entity_type"] in policy_entities and 
                            "encrypted_value" in entity):
                            entities_to_encrypt.append(entity)
            
            # Sort by start position descending
            entities_to_encrypt.sort(key=lambda x: x["start"], reverse=True)
            
            # Replace original values with encrypted values in text
            for entity in entities_to_encrypt:
                start = entity["start"]
                end = entity["end"]
                original = entity.get("original_value", entity["value"])
                encrypted = entity["encrypted_value"]
                
                # Replace in text
                if encrypted_text[start:end] == original:
                    encrypted_text = encrypted_text[:start] + encrypted + encrypted_text[end:]
                    logger.debug(f"Replaced {original} with encrypted value at position {start}-{end}")
                else:
                    logger.warning(f"Text mismatch at position {start}-{end}: expected '{original}', found '{encrypted_text[start:end]}'")
            
            logger.info(f"Text encrypted: {len(entities_to_encrypt)} entities replaced")
        
        # Prepare applied policies information
        applied_policies = []
        for policy in matching_policies:
            policy_entities = policy.entity_types or []
            relevant_entities = [
                e for e in detected_entities 
                if e["entity_type"] in policy_entities
            ]
            applied_policies.append({
                "id": str(policy.id),
                "name": policy.name,
                "action": policy.action,
                "severity": policy.severity,
                "entity_types": policy_entities,
                "matched_entities": [e["entity_type"] for e in relevant_entities],
                "matched_count": len(relevant_entities)
            })
        
        return {
            "sensitive_data_detected": len(detected_entities) > 0,
            "detected_entities": detected_entities,
            "actions_taken": actions_taken,
            "blocked": blocked,
            "alert_created": alert_created,
            "policies_matched": len(matching_policies) > 0,
            "applied_policies": applied_policies,
            "encrypted_text": encrypted_text
        }
    
    async def _create_alert(self, policy: Policy, detected_entities: List[Dict],
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
                title=policy.name,  # Use policy name as title
                description=f"Detected {len(detected_entities)} sensitive entities",
                severity=severity,
                status=AlertStatus.PENDING,
                source_ip=source_ip,
                source_user=source_user,
                source_device=source_device,
                detected_entities=detected_entities,
                policy_id=str(policy.id),
                action_taken=policy.action,
                blocked=blocked
            )
            
            await alert.insert()
            logger.info(f"Alert created: {alert.id}")
            
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
    
    async def _log_event(self, event_type: str, message: str,
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
            await log.insert()
            
        except Exception as e:
            logger.error(f"Error logging event: {e}")
    
    async def _store_detected_entity(self, entity: Dict, source_text_hash: str):
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
            
            await detected_entity.insert()
            
        except Exception as e:
            logger.error(f"Error storing detected entity: {e}")
