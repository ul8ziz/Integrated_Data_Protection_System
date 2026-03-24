"""
Email monitoring service for detecting and blocking sensitive data in emails - MongoDB version
"""
import logging
import base64
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.services.presidio_service import PresidioService
from app.services.policy_service import PolicyService
from app.services.mydlp_service import MyDLPService
from app.services.file_extractor_service import FileTextExtractor
from app.models_mongo.logs import Log, DetectedEntity
from app.models_mongo.alerts import Alert, AlertSeverity, AlertStatus
from datetime import datetime
from app.utils.datetime_utils import get_current_time

logger = logging.getLogger(__name__)

# Stored in inbox log for preview + on-demand re-analysis (avoid tiny 500-char clip)
EMAIL_LOG_BODY_PREVIEW_MAX = 20000


class EmailMonitoringService:
    """Service for monitoring and analyzing emails for sensitive data"""
    
    def __init__(self):
        """Initialize email monitoring service"""
        self.presidio = PresidioService()
        self.policy_service = PolicyService()
        self.mydlp = MyDLPService()
        self.file_extractor = FileTextExtractor()

    @staticmethod
    def _serialize_entities_for_log(entities: List[Dict], max_value_len: int = 120) -> List[Dict[str, Any]]:
        """JSON-safe entity list for inbox / log display (truncated values)."""
        out: List[Dict[str, Any]] = []
        for e in entities or []:
            v = e.get("value")
            if v is None:
                v = ""
            else:
                v = str(v)
            if len(v) > max_value_len:
                v = v[:max_value_len] + "…"
            sc = e.get("score")
            try:
                sc = round(float(sc), 4) if sc is not None else None
            except (TypeError, ValueError):
                sc = None
            out.append({
                "entity_type": e.get("entity_type"),
                "score": sc,
                "value": v,
            })
        return out

    @staticmethod
    def _applied_policies_summary(policy_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        apps = policy_result.get("applied_policies") or []
        return [
            {
                "name": p.get("name"),
                "action": p.get("action"),
                "severity": p.get("severity"),
            }
            for p in apps[:30]
        ]
    
    async def analyze_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze email content for sensitive data
        
        Args:
            email_data: Email information containing:
                - from: Sender email address
                - to: List of recipient email addresses
                - subject: Email subject
                - body: Email body text
                - attachments: Optional list. Each item is either a string (filename) or
                  dict with "filename" and "content" (base64-encoded file content).
                  If content is provided, attachment text is extracted and analyzed.
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
            
            # Build list of attachment file names (for logs, alerts, operations)
            attachment_names = []
            for att in attachments:
                if isinstance(att, dict) and att.get("filename"):
                    attachment_names.append(att["filename"])
                elif isinstance(att, str):
                    attachment_names.append(att)
            
            # Extract and analyze attachment content if present; keep per-file content for log display
            attachment_texts = []
            attachment_contents: List[dict] = []  # [{"filename": "...", "content": "..."}]
            _max_content_len = 5000  # cap per-file content stored in log
            for att in attachments:
                if isinstance(att, dict) and att.get("content") and att.get("filename"):
                    try:
                        raw = base64.b64decode(att["content"])
                        if not raw:
                            continue
                        filename = att["filename"]
                        ext = Path(filename).suffix.lower()
                        if not self.file_extractor.is_supported(filename):
                            logger.debug(f"Unsupported attachment format: {filename}")
                            continue
                        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                            tmp.write(raw)
                            tmp_path = tmp.name
                        try:
                            text = self.file_extractor.extract_text(tmp_path, file_content=raw)
                            if text and text.strip():
                                attachment_texts.append(f"[Attachment: {filename}]\n{text.strip()}")
                                content = text.strip()
                                if len(content) > _max_content_len:
                                    content = content[:_max_content_len] + "\n[... truncated ...]"
                                attachment_contents.append({"filename": filename, "content": content})
                        finally:
                            try:
                                os.unlink(tmp_path)
                            except Exception:
                                pass
                    except Exception as e:
                        logger.warning(f"Failed to extract text from attachment {att.get('filename', '?')}: {e}")
            
            if attachment_texts:
                full_text += "\n\n" + "\n\n".join(attachment_texts)
            
            # Analyze with Presidio
            detected_entities = self.presidio.analyze(full_text)
            
            # We will log the email event after we know the result (so we can store encrypted body for recipient when action=encrypt)
            log_body_preview = body[:EMAIL_LOG_BODY_PREVIEW_MAX] if body else ""
            log_extra_data = {
                "from": from_email,
                "to": to_emails,
                "subject": subject,
                "has_attachments": len(attachments) > 0,
                "attachment_count": len(attachments),
                "attachment_names": attachment_names,
            }
            if attachment_contents:
                log_extra_data["attachment_contents"] = attachment_contents

            if not detected_entities:
                log_extra_data["body_preview"] = log_body_preview
                log_extra_data["sensitive_data_detected"] = False
                log_extra_data["detected_entities"] = []
                await self._log_email_event(
                    event_type="email_received",
                    message=f"Email from {from_email} to {', '.join(to_emails)}",
                    source_ip=source_ip,
                    source_user=source_user,
                    email_data=log_extra_data
                )
                return {
                    "sensitive_data_detected": False,
                    "detected_entities": [],
                    "action": "allow",
                    "blocked": False,
                    "message": "No sensitive data detected"
                }
            
            # Apply policies with detected entities (mark alerts as from email for Blocked Emails stats)
            alert_extra = {"source": "email", "to": to_emails, "body_preview": log_body_preview}
            if attachment_contents:
                alert_extra["attachment_contents"] = attachment_contents
            policy_result = await self.policy_service.apply_policy_with_entities(
                detected_entities=detected_entities,
                text=full_text,
                source_ip=source_ip,
                source_user=source_user,
                source_device="email_client",
                source_attachment_names=attachment_names if attachment_names else None,
                alert_extra_data=alert_extra
            )
            
            # Determine action based on policy result
            # Only take action if policies matched
            if not policy_result.get("policies_matched", False):
                # No policies matched - allow email and don't create alerts
                logger.info(f"Email from {from_email} allowed - no matching policies for detected entities")
                logger.info(f"Detected entity types: {[e['entity_type'] for e in detected_entities]}")
                logger.info(f"Available policies: {[p.name for p in await self.policy_service.get_active_policies()]}")
                log_extra_data["body_preview"] = log_body_preview
                log_extra_data["sensitive_data_detected"] = True
                log_extra_data["detected_entities"] = self._serialize_entities_for_log(detected_entities)
                log_extra_data["policies_matched"] = False
                log_extra_data["analysis_action"] = "allow"
                await self._log_email_event(
                    event_type="email_received",
                    message=f"Email from {from_email} to {', '.join(to_emails)}",
                    source_ip=source_ip,
                    source_user=source_user,
                    email_data=log_extra_data
                )
                return {
                    "sensitive_data_detected": True,
                    "detected_entities": detected_entities,
                    "action": "allow",
                    "blocked": False,
                    "alert_created": False,
                    "policies_matched": False,
                    "applied_policies": [],
                    "actions_taken": [],
                    "encrypted_text": None,
                    "message": f"Email allowed - {len(detected_entities)} entities detected but no matching policies"
                }
            
            # Determine action from policy result (priority: block > encrypt > alert > allow)
            # block  = منع الإرسال + إشعار للمدير
            # alert  = السماح بالإرسال + إشعار للمدير
            # encrypt = إشعار للمدير + السماح بالإرسال مع تطبيق التشفير على المحتوى
            action = "allow"
            if policy_result.get("blocked", False):
                action = "block"
            elif policy_result.get("encrypted_text"):
                action = "encrypt"
            elif policy_result.get("alert_created", False):
                action = "alert"
            
            # block: prevent sending email + notify manager (alert already created by policy_service)
            if action == "block":
                self.mydlp.block_email(
                    email_id=f"{from_email}_{get_current_time().isoformat()}",
                    reason=f"Policy violation: {len(detected_entities)} sensitive entities detected"
                )
                logger.info(f"Email blocked by policy - alert already created by policy service")
            
            # When action is encrypt: build encrypted_body (what recipient should receive)
            encrypted_body = None
            encrypted_subject = None
            if action == "encrypt" and policy_result.get("encrypted_text"):
                body_start = len(subject) + 2  # after "subject\n\n"
                body_end = body_start + len(body)
                det = policy_result.get("detected_entities", [])
                body_entities = [
                    e for e in det
                    if e.get("encrypted_value") and e["start"] >= body_start and e["end"] <= body_end
                ]
                body_entities.sort(key=lambda x: x["start"], reverse=True)
                encrypted_body = body
                for e in body_entities:
                    start_rel = e["start"] - body_start
                    end_rel = e["end"] - body_start
                    orig = e.get("original_value", e.get("value", ""))
                    if encrypted_body[start_rel:end_rel] == orig:
                        encrypted_body = encrypted_body[:start_rel] + e["encrypted_value"] + encrypted_body[end_rel:]
                # Encrypt subject if any entity is in subject (subject is 0 to len(subject))
                subject_entities = [
                    e for e in det
                    if e.get("encrypted_value") and e["start"] < body_start and e["end"] <= body_start
                ]
                if subject_entities:
                    subject_entities.sort(key=lambda x: x["start"], reverse=True)
                    encrypted_subject = subject
                    for e in subject_entities:
                        if encrypted_subject[e["start"]:e["end"]] == e.get("original_value", e.get("value", "")):
                            encrypted_subject = encrypted_subject[:e["start"]] + e["encrypted_value"] + encrypted_subject[e["end"]:]
                else:
                    encrypted_subject = subject
            
            # Store detected entities only if policies matched
            if policy_result.get("policies_matched", False):
                for entity in detected_entities:
                    await self._store_detected_entity(
                        entity=entity,
                        source_text_hash=self.policy_service.encryption.hash_text(full_text),
                        source_file=f"email_{from_email}_{get_current_time().timestamp()}"
                    )
            
            # Log email so it appears in inbox (only when email is sent: allow/alert/encrypt, not block)
            if action != "block":
                log_extra_data["body_preview"] = (
                    (encrypted_body[:EMAIL_LOG_BODY_PREVIEW_MAX] if encrypted_body else log_body_preview)
                    if action == "encrypt" and encrypted_body
                    else log_body_preview
                )
                if action == "encrypt" and encrypted_body:
                    log_extra_data["encrypted_body"] = encrypted_body  # ما سيصل للمستلم
                    # Store original body encrypted so recipient can decrypt (فك التشفير)
                    try:
                        log_extra_data["original_body_encrypted"] = self.policy_service.encryption.encrypt(body)
                    except Exception as enc_err:
                        logger.warning(f"Could not store encrypted original body for decrypt: {enc_err}")
                if action == "encrypt" and encrypted_subject is not None:
                    log_extra_data["subject"] = encrypted_subject  # عرض الموضوع المشفر للمستلم
                    try:
                        log_extra_data["original_subject_encrypted"] = self.policy_service.encryption.encrypt(subject)
                    except Exception as enc_err:
                        logger.warning(f"Could not store encrypted original subject for decrypt: {enc_err}")
                log_extra_data["sensitive_data_detected"] = True
                log_extra_data["detected_entities"] = self._serialize_entities_for_log(detected_entities)
                log_extra_data["policies_matched"] = policy_result.get("policies_matched", False)
                log_extra_data["analysis_action"] = action
                log_extra_data["applied_policies_summary"] = self._applied_policies_summary(policy_result)
                if action == "encrypt":
                    log_extra_data["encrypted"] = True
                    log_extra_data["encryption_method"] = "AES-256"
                elif action == "alert":
                    log_extra_data["alert_triggered"] = True
                    log_extra_data["alert_severity"] = policy_result.get("highest_severity", "medium")
                await self._log_email_event(
                    event_type="email_received",
                    message=f"Email from {from_email} to {', '.join(to_emails)}",
                    source_ip=source_ip,
                    source_user=source_user,
                    email_data=log_extra_data
                )
            
            return {
                "sensitive_data_detected": True,
                "detected_entities": detected_entities,
                "action": action,
                "blocked": action == "block",
                "alert_created": policy_result.get("alert_created", False),
                "policies_matched": policy_result.get("policies_matched", False),
                "applied_policies": policy_result.get("applied_policies", []),
                "actions_taken": policy_result.get("actions_taken", []),
                "encrypted_text": policy_result.get("encrypted_text"),
                "encrypted_body": encrypted_body,
                "encrypted_subject": encrypted_subject,
                "message": (
                    "Email blocked — لا يتم إرسال الإيميل، تم إشعار المدير." if action == "block"
                    else "Email allowed with encryption — تم تطبيق التشفير على المحتوى وإشعار المدير. يمكن إرسال الإيميل بالمحتوى المشفر." if action == "encrypt"
                    else "Email allowed — تم إرسال الإيميل مع إشعار المدير." if action == "alert"
                    else f"Email allowed — {len(detected_entities)} entities detected"
                )
            }
            
        except Exception as e:
            logger.error(f"Error analyzing email: {e}")
            return {
                "sensitive_data_detected": False,
                "error": str(e),
                "action": "allow",
                "blocked": False
            }
    
    async def _log_email_event(self, event_type: str, message: str,
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
            await log.insert()
        except Exception as e:
            logger.error(f"Error logging email event: {e}")
    
    async def _create_email_alert(self, from_email: str, to_emails: List[str],
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
                blocked=blocked,
                detected_entities=detected_entities,
                extra_data={"to": to_emails}
            )
            
            await alert.insert()
            logger.info(f"Email alert created: {alert.id}")
            
        except Exception as e:
            logger.error(f"Error creating email alert: {e}")
    
    async def decrypt_email_content_for_recipient(
        self, log_id: str, recipient_identifiers: List[str]
    ) -> Dict[str, Any]:
        """
        Decrypt stored original body/subject for an email log. Only allowed if the
        recipient is in the log's 'to' list (so the recipient can use فك التشفير).
        Returns dict with decrypted content, or dict with "error" key for specific failure reason.
        """
        if not recipient_identifiers:
            return {"error": "forbidden"}
        try:
            from beanie import PydanticObjectId
            from bson.errors import InvalidId
            try:
                oid = PydanticObjectId(log_id)
            except (InvalidId, TypeError, ValueError, Exception):
                return {"error": "not_found"}
            log = await Log.get(oid)
            if not log:
                return {"error": "not_found"}
            if log.event_type != "email_received":
                return {"error": "not_found"}
            extra = log.extra_data or {}
            to_list = extra.get("to") or []
            if not to_list:
                return {"error": "not_recipient"}
            to_set = set(str(x).strip().lower() for x in to_list)
            if not any(str(rid).strip().lower() in to_set for rid in recipient_identifiers):
                return {"error": "not_recipient"}
            body_enc = extra.get("original_body_encrypted")
            subject_enc = extra.get("original_subject_encrypted")
            if not body_enc and not subject_enc:
                return {"error": "no_decryptable_content"}
            out = {}
            if body_enc:
                try:
                    out["body"] = self.policy_service.encryption.decrypt(body_enc)
                except Exception as e:
                    logger.warning(f"Decrypt body failed: {e}")
                    out["body"] = None
            if subject_enc:
                try:
                    out["subject"] = self.policy_service.encryption.decrypt(subject_enc)
                except Exception as e:
                    logger.warning(f"Decrypt subject failed: {e}")
                    out["subject"] = None
            return out if out else {"error": "decrypt_failed"}
        except Exception as e:
            logger.error(f"decrypt_email_content_for_recipient error: {e}")
            return {"error": "not_found"}

    def _build_text_from_stored_email_extra(self, extra: Dict[str, Any]) -> str:
        """Rebuild analysis text from log extra_data (decrypt originals when stored)."""
        subject = extra.get("subject") or ""
        subj_enc = extra.get("original_subject_encrypted")
        if subj_enc:
            try:
                subject = self.policy_service.encryption.decrypt(subj_enc)
            except Exception:
                pass
        body_text = ""
        obe = extra.get("original_body_encrypted")
        if obe:
            try:
                body_text = self.policy_service.encryption.decrypt(obe)
            except Exception:
                body_text = ""
        if not body_text:
            body_text = extra.get("body_preview") or ""
        full_text = f"{subject}\n\n{body_text}" if subject else body_text
        for ac in extra.get("attachment_contents") or []:
            fn = ac.get("filename", "") or ""
            content = (ac.get("content") or "").strip()
            if content:
                full_text += "\n\n[Attachment: %s]\n%s" % (fn, content)
        max_len = 100000
        if len(full_text) > max_len:
            return full_text[:max_len] + "\n[... truncated for analysis ...]"
        return full_text

    async def reanalyze_email_log_for_recipient(
        self, log_id: str, recipient_identifiers: List[str]
    ) -> Dict[str, Any]:
        """
        Re-run Presidio on text stored in the email log. Only the recipient may call.
        Uses snapshot when already stored; otherwise analyzes body_preview + attachments
        (and decrypted originals when available).
        """
        if not recipient_identifiers:
            return {"error": "forbidden"}
        try:
            from beanie import PydanticObjectId
            from bson.errors import InvalidId
            try:
                oid = PydanticObjectId(log_id)
            except (InvalidId, TypeError, ValueError, Exception):
                return {"error": "not_found"}
            log = await Log.get(oid)
            if not log or log.event_type != "email_received":
                return {"error": "not_found"}
            extra = log.extra_data or {}
            to_list = extra.get("to") or []
            if not to_list:
                return {"error": "not_recipient"}
            to_set = set(str(x).strip().lower() for x in to_list)
            if not any(str(rid).strip().lower() in to_set for rid in recipient_identifiers):
                return {"error": "not_recipient"}

            snap = extra.get("detected_entities")
            if isinstance(snap, list):
                if len(snap) > 0:
                    return {
                        "sensitive_data_detected": bool(extra.get("sensitive_data_detected", True)),
                        "detected_entities": snap,
                        "source": "from_log_snapshot",
                    }
                if extra.get("sensitive_data_detected") is False:
                    return {
                        "sensitive_data_detected": False,
                        "detected_entities": [],
                        "source": "from_log_snapshot",
                    }

            full_text = self._build_text_from_stored_email_extra(extra)
            if not full_text or not str(full_text).strip():
                return {
                    "sensitive_data_detected": False,
                    "detected_entities": [],
                    "source": "recomputed",
                    "note": "no_stored_text",
                }

            raw_entities = self.presidio.analyze(full_text)
            serialized = self._serialize_entities_for_log(raw_entities)
            # Heuristic: logs before EMAIL_LOG_BODY_PREVIEW_MAX stored only 500 chars of body
            bp = extra.get("body_preview") or ""
            legacy_short = (not extra.get("original_body_encrypted")) and len(bp) == 500
            out = {
                "sensitive_data_detected": len(serialized) > 0,
                "detected_entities": serialized,
                "source": "recomputed_from_stored_text",
            }
            if legacy_short:
                out["legacy_short_preview"] = True
                out["note"] = (
                    "This log was saved with an older body preview limit (500 characters). "
                    "Re-send the email after upgrading the server for full analysis."
                )
            return out
        except Exception as e:
            logger.error(f"reanalyze_email_log_for_recipient error: {e}", exc_info=True)
            return {"error": "not_found"}
    
    async def _store_detected_entity(self, entity: Dict, source_text_hash: str,
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
            
            await detected_entity.insert()
            
        except Exception as e:
            logger.error(f"Error storing detected entity: {e}")
    
    async def get_email_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        Get email monitoring statistics
        
        Args:
            days: Number of days to look back
            
        Returns:
            Statistics dictionary
        """
        try:
            from datetime import timedelta
            start_date = get_current_time() - timedelta(days=days)
            
            # Count email events
            email_logs = await Log.find({
                "event_type": "email_received",
                "created_at": {"$gte": start_date}
            }).count()
            
            # Count blocked emails: alerts from email flow (title "Email blocked..." or extra_data.source "email")
            blocked_email_alerts = await Alert.find({
                "created_at": {"$gte": start_date},
                "blocked": True,
                "$or": [
                    {"title": {"$regex": "^Email blocked"}},
                    {"extra_data.source": "email"}
                ]
            }).count()
            
            # Count detected entities in emails
            email_entities = await DetectedEntity.find({
                "created_at": {"$gte": start_date},
                "source_file": {"$regex": "^email_"}
            }).count()
            
            return {
                "period_days": days,
                "total_emails_analyzed": email_logs,
                "blocked_emails": blocked_email_alerts,
                "detected_entities": email_entities,
                "allowed_emails": email_logs - blocked_email_alerts
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
