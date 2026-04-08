"""
API routes for monitoring and reports
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query, Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from app.utils.datetime_utils import get_current_time, format_datetime_server, to_iso_utc
from app.utils.audit_sanitize import sanitize_extra_data
from app.models_mongo.logs import Log, DetectedEntity
from app.models_mongo.alerts import Alert
from app.models_mongo.policies import Policy
from app.services.mydlp_service import MyDLPService
from app.services.email_monitoring_service import EmailMonitoringService
from app.api.dependencies import get_current_admin, get_optional_user, get_current_user

router = APIRouter(prefix="/api/monitoring", tags=["Monitoring"])

# Initialize services
# Note: MyDLPService reads config at initialization, so it will use the latest config
# when the module is loaded. If config changes, server restart is needed.
mydlp_service = MyDLPService()
email_monitoring = EmailMonitoringService()

# Log initial MyDLP status for debugging
import logging
logger = logging.getLogger(__name__)
logger.info(f"MyDLP service initialized - enabled: {mydlp_service.is_enabled()}, API URL: {mydlp_service.api_url}")


async def _policy_names_from_matching_ids(meta: Optional[Dict[str, Any]]) -> List[str]:
    """Resolve matching_policy_ids in log metadata to policy display names."""
    if not meta:
        return []
    ids = meta.get("matching_policy_ids") or []
    if not ids:
        return []
    from bson import ObjectId

    oids = []
    for pid in ids:
        try:
            oids.append(ObjectId(pid))
        except Exception:
            pass
    if not oids:
        return [str(i) for i in ids]
    policies = await Policy.find({"_id": {"$in": oids}}).to_list()
    policy_id_to_name = {str(p.id): (p.name or str(p.id)) for p in policies}
    return [policy_id_to_name.get(str(pid), str(pid)) for pid in ids]


@router.get("/status")
async def get_system_status(
    current_user = Depends(get_current_admin)  # Admin only
):
    """
    Get system status and component health
    """
    # Read MyDLP enabled status directly from environment variable
    # This ensures we always get the current value, even if server wasn't restarted
    import os
    from dotenv import load_dotenv
    
    # Reload .env file to get latest values
    # Try multiple possible paths for .env file
    current_dir = os.path.dirname(__file__)  # app/api/routes/
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))  # backend/
    env_path = os.path.join(backend_dir, '.env')
    if not os.path.exists(env_path):
        # Fallback: try current working directory
        env_path = os.path.join(os.getcwd(), '.env')
    load_dotenv(env_path, override=True)
    
    # Read MYDLP_ENABLED directly from environment
    _mydlp_env = os.getenv("MYDLP_ENABLED", "").strip().lower()
    if _mydlp_env in ("false", "0", "no", "off"):
        mydlp_enabled = False
    else:
        # Default to True (if empty or any other value)
        mydlp_enabled = True
    
    # Create MyDLP service
    current_mydlp = MyDLPService()
    # Override enabled status with fresh value from env
    current_mydlp.enabled = mydlp_enabled
    
    return {
        "status": "operational",
        "presidio": {
            "enabled": True,
            "status": "operational"
        },
        "mydlp": {
            "enabled": mydlp_enabled,
            "status": "operational" if mydlp_enabled else "disabled",
            "is_localhost": current_mydlp.is_local() if mydlp_enabled else False
        },
        "timestamp": get_current_time().isoformat()
    }


@router.post("/traffic")
async def monitor_traffic(
    traffic_data: Dict[str, Any],
    current_user = Depends(get_current_admin)  # Admin only
):
    """
    Monitor network traffic for sensitive data
    
    This endpoint receives traffic data and uses MyDLP to monitor it
    """
    try:
        result = mydlp_service.monitor_network_traffic(traffic_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error monitoring traffic: {str(e)}")


@router.get("/reports/summary")
async def get_summary_report(
    days: int = 7,
    current_user = Depends(get_current_admin)  # Admin only
):
    """
    Get summary report for the last N days
    """
    try:
        start_date = get_current_time() - timedelta(days=days)
        
        # Count logs
        total_logs = await Log.find({"created_at": {"$gte": start_date}}).count()
        
        # Count detected entities
        total_entities = await DetectedEntity.find({"created_at": {"$gte": start_date}}).count()
        
        # Count alerts
        total_alerts = await Alert.find({"created_at": {"$gte": start_date}}).count()
        blocked_count = await Alert.find({
            "created_at": {"$gte": start_date},
            "blocked": True
        }).count()
        
        # Count policies
        active_policies = await Policy.find({"enabled": True}).count()
        
        # Entity type breakdown
        entities = await DetectedEntity.find({"created_at": {"$gte": start_date}}).to_list()
        entity_type_counts = {}
        for entity in entities:
            entity_type = entity.entity_type
            entity_type_counts[entity_type] = entity_type_counts.get(entity_type, 0) + 1
        
        return {
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": get_current_time().isoformat(),
            "summary": {
                "total_logs": total_logs,
                "total_detected_entities": total_entities,
                "total_alerts": total_alerts,
                "blocked_attempts": blocked_count,
                "active_policies": active_policies
            },
            "entity_type_breakdown": entity_type_counts
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")


@router.get("/reports/logs")
async def get_logs_report(
    event_type: str = None,
    level: str = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user = Depends(get_current_admin)  # Admin only
):
    """
    Get logs report with pagination
    
    Query parameters:
    - event_type: Filter by event type
    - level: Filter by log level
    - page: Page number (default: 1)
    - limit: Items per page (default: 10, max: 100)
    """
    try:
        query = {}
        if event_type:
            query["event_type"] = event_type
        if level:
            query["level"] = level
        
        # Calculate pagination
        skip = (page - 1) * limit
        
        # Get total count
        if query:
            total_count = await Log.find(query).count()
            logs = await Log.find(query).sort("-created_at").skip(skip).limit(limit).to_list()
        else:
            total_count = await Log.find({}).count()
            logs = await Log.find({}).sort("-created_at").skip(skip).limit(limit).to_list()
        
        # Calculate pagination metadata
        total_pages = (total_count + limit - 1) // limit if total_count > 0 else 0
        
        return {
            "items": [
                {
                    "id": str(log.id),
                    "event_type": log.event_type,
                    "message": log.message,
                    "level": log.level,
                    "source_ip": log.source_ip,
                    "source_user": log.source_user,
                    "created_at": to_iso_utc(log.created_at),
                    "created_at_server": format_datetime_server(log.created_at),
                    "metadata": sanitize_extra_data(log.extra_data) if log.extra_data else None,
                }
                for log in logs
            ],
            "total": total_count,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching logs: {str(e)}")


@router.get("/operations/{log_id}")
async def get_operation_audit(
    log_id: str,
    include_binary_attachment_payloads: bool = Query(
        False,
        description="When true, includes raw base64 attachment payloads (admin download / forensics).",
    ),
    current_user=Depends(get_current_admin),
):
    """
    Full single-operation record for admin audit. By default metadata is redacted for large binary fields.
    Set include_binary_attachment_payloads=true to retrieve stored attachment bytes (same as inbox download).
    """
    try:
        from beanie import PydanticObjectId
        from bson.errors import InvalidId

        try:
            oid = PydanticObjectId(log_id)
        except (InvalidId, TypeError, ValueError, Exception):
            raise HTTPException(status_code=404, detail="Log not found")
        log = await Log.get(oid)
        if not log:
            raise HTTPException(status_code=404, detail="Log not found")
        raw_meta = log.extra_data or {}
        if include_binary_attachment_payloads:
            meta: Any = raw_meta
        else:
            meta = sanitize_extra_data(raw_meta)
        policy_names = await _policy_names_from_matching_ids(raw_meta)
        return {
            "id": str(log.id),
            "event_type": log.event_type,
            "message": log.message,
            "level": log.level,
            "source_ip": log.source_ip,
            "source_user": log.source_user,
            "user_agent": log.user_agent,
            "file_name": log.file_name,
            "file_size": log.file_size,
            "file_type": log.file_type,
            "network_destination": log.network_destination,
            "network_protocol": log.network_protocol,
            "created_at": to_iso_utc(log.created_at),
            "created_at_server": format_datetime_server(log.created_at),
            "metadata": meta,
            "policy_names": policy_names,
            "payloads_included": include_binary_attachment_payloads,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_operation_audit: {e}")
        raise HTTPException(status_code=500, detail="Error loading operation log")


@router.post("/email")
async def monitor_email(
    email_data: Dict[str, Any],
    http_request: Request
):
    """
    Monitor and analyze email for sensitive data
    Available to all authenticated users
    
    This endpoint receives email data and analyzes it for sensitive information.
    If sensitive data is detected, the email may be blocked based on policies.
    
    Request body:
    {
        "from": "sender@example.com",
        "to": ["recipient@example.com"],
        "subject": "Email subject",
        "body": "Email body text",
        "attachments": [{"filename": "file.pdf", "content": "base64_encoded_content"}],  # optional; content is extracted and analyzed
        "source_ip": "127.0.0.1",  # optional, defaults to 127.0.0.1
        "source_user": "user@example.com"  # optional
    }
    """
    # Optional: get current user if authenticated (not required, but preferred)
    current_user = await get_optional_user(http_request)
    try:
        result = await email_monitoring.analyze_email(email_data=email_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error monitoring email: {str(e)}")


@router.get("/email/statistics")
async def get_email_statistics(
    days: int = 7,
    current_user = Depends(get_current_admin)  # Admin only
):
    """
    Get email monitoring statistics
    
    Returns statistics about emails analyzed, blocked, and detected entities.
    """
    try:
        stats = await email_monitoring.get_email_statistics(days=days)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting email statistics: {str(e)}")


@router.get("/email/logs")
async def get_email_logs(
    limit: int = 50,
    current_user = Depends(get_current_admin)  # Admin only
):
    """
    Get email monitoring logs
    
    Returns recent email analysis logs.
    """
    try:
        logs = await Log.find({"event_type": "email_received"}).sort("-created_at").limit(limit).to_list()
        
        return {
            "count": len(logs),
            "logs": [
                {
                    "id": str(log.id),
                    "message": log.message,
                    "level": log.level,
                    "source_ip": log.source_ip,
                    "source_user": log.source_user,
                    "created_at": to_iso_utc(log.created_at),
                    "created_at_server": format_datetime_server(log.created_at),
                    "email_data": log.extra_data
                }
                for log in logs
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching email logs: {str(e)}")


@router.get("/email/list")
async def get_email_list_inbox(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user = Depends(get_current_user)
):
    """
    Get emails sent TO the current user (inbox).
    Returns only logs where current user's email or username is in the 'to' list.
    """
    try:
        recipient_identifiers = []
        if getattr(current_user, "email", None):
            recipient_identifiers.append(current_user.email)
        if getattr(current_user, "username", None) and current_user.username not in recipient_identifiers:
            recipient_identifiers.append(current_user.username)
        if not recipient_identifiers:
            return {"count": 0, "logs": [], "page": page, "limit": limit, "total": 0}

        query = {
            "event_type": "email_received",
            "extra_data.to": {"$in": recipient_identifiers}
        }
        skip = (page - 1) * limit
        total = await Log.find(query).count()
        logs = await Log.find(query).sort("-created_at").skip(skip).limit(limit).to_list()

        return {
            "count": len(logs),
            "total": total,
            "page": page,
            "limit": limit,
            "logs": [
                {
                    "id": str(log.id),
                    "message": log.message,
                    "level": log.level,
                    "source_ip": log.source_ip,
                    "source_user": log.source_user,
                    "created_at": to_iso_utc(log.created_at),
                    "created_at_server": format_datetime_server(log.created_at),
                    "email_data": log.extra_data
                }
                for log in logs
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching email list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching email list: {str(e)}")


@router.get("/email/log/{log_id}")
async def get_email_log_detail(
    log_id: str,
    current_user=Depends(get_current_user),
):
    """
    Full stored email_data for one inbox message (includes attachment_files for download).
    Only if the current user is listed as a recipient on the message.
    """
    try:
        from beanie import PydanticObjectId
        from bson.errors import InvalidId

        try:
            oid = PydanticObjectId(log_id)
        except (InvalidId, TypeError, ValueError, Exception):
            raise HTTPException(status_code=404, detail="Email not found")
        log = await Log.get(oid)
        if not log or log.event_type != "email_received":
            raise HTTPException(status_code=404, detail="Email not found")
        extra = log.extra_data or {}
        recipient_identifiers = []
        if getattr(current_user, "email", None):
            recipient_identifiers.append(current_user.email)
        if getattr(current_user, "username", None) and current_user.username not in recipient_identifiers:
            recipient_identifiers.append(current_user.username)
        if not recipient_identifiers:
            raise HTTPException(status_code=403, detail="Cannot identify recipient")
        to_list = extra.get("to") or []
        if not to_list:
            raise HTTPException(status_code=403, detail="Access denied")
        to_set = set(str(x).strip().lower() for x in to_list)
        if not any(str(rid).strip().lower() in to_set for rid in recipient_identifiers):
            raise HTTPException(status_code=403, detail="You are not a recipient of this email.")
        return {
            "id": str(log.id),
            "email_data": extra,
            "message": log.message,
            "created_at": to_iso_utc(log.created_at),
            "created_at_server": format_datetime_server(log.created_at),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_email_log_detail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error loading email")


@router.get("/email/log/{log_id}/analysis")
async def get_email_log_analysis(
    log_id: str = Path(..., description="MongoDB log id of the email_received event"),
    current_user=Depends(get_current_user),
):
    """
    PII analysis for an inbox email log: uses stored snapshot when present,
    otherwise re-runs Presidio on body_preview / decrypted originals + attachment text.
    Only recipients listed on the email may access.
    """
    recipient_identifiers = []
    if getattr(current_user, "email", None):
        recipient_identifiers.append(current_user.email)
    if getattr(current_user, "username", None) and current_user.username not in recipient_identifiers:
        recipient_identifiers.append(current_user.username)
    if not recipient_identifiers:
        raise HTTPException(status_code=403, detail="Cannot identify recipient")

    result = await email_monitoring.reanalyze_email_log_for_recipient(log_id, recipient_identifiers)
    err = result.get("error") if isinstance(result, dict) else None
    if err == "not_found":
        raise HTTPException(status_code=404, detail="Email log not found.")
    if err == "not_recipient":
        raise HTTPException(status_code=403, detail="You are not a recipient of this email.")
    if err == "forbidden":
        raise HTTPException(status_code=403, detail="Access denied.")
    return result


@router.get("/email/decrypt")
async def decrypt_email_for_recipient(
    log_id: str = Query(..., description="Log ID of the email to decrypt"),
    current_user = Depends(get_current_user)
):
    """
    Decrypt the original body/subject of an email for the recipient (فك التشفير).
    Only allowed if the current user is in the email's 'to' list.
    """
    recipient_identifiers = []
    if getattr(current_user, "email", None):
        recipient_identifiers.append(current_user.email)
    if getattr(current_user, "username", None) and current_user.username not in recipient_identifiers:
        recipient_identifiers.append(current_user.username)
    if not recipient_identifiers:
        raise HTTPException(status_code=403, detail="Cannot identify recipient")
    result = await email_monitoring.decrypt_email_content_for_recipient(log_id, recipient_identifiers)
    err = result.get("error") if isinstance(result, dict) else None
    if err == "not_found":
        raise HTTPException(status_code=404, detail="Email not found or invalid ID.")
    if err == "not_recipient":
        raise HTTPException(status_code=403, detail="You are not a recipient of this email.")
    if err == "no_decryptable_content":
        return {
            "decrypted": False,
            "message": "This email was not stored with decryptable content. Only emails encrypted after the feature was enabled support decryption. / هذا الإيميل لم يُحفظ بمحتوى قابل لفك التشفير."
        }
    if err == "decrypt_failed":
        raise HTTPException(status_code=500, detail="Decryption failed.")
    if err == "forbidden":
        raise HTTPException(status_code=403, detail="Cannot identify recipient")
    if isinstance(result, dict) and ("body" in result or "subject" in result):
        return result
    raise HTTPException(status_code=404, detail="Email not found or no content to decrypt.")


@router.get("/user-activities/{user_id}")
async def get_user_activities(
    user_id: str,
    days: int = Query(30, ge=1, le=365),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user = Depends(get_current_admin)  # Admin only
):
    """
    Get activities for a specific user with pagination.
    
    Returns:
    - Paginated operations (all, file, network, analysis)
    - Summary counts for the full period
    - pagination: page, limit, total, total_pages, has_next, has_prev
    """
    try:
        from datetime import datetime, timedelta
        from app.models_mongo.users import User
        
        # Verify user exists
        user = await User.get(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        start_date = get_current_time() - timedelta(days=days)
        query = {
            "$and": [
                {"created_at": {"$gte": start_date}},
                {"$or": [
                    {"source_user": user.username},
                    {"source_user": user.email}
                ]}
            ]
        }
        
        # Total count for the period (for summary and pagination)
        total_count = await Log.find(query).count()
        total_pages = (total_count + limit - 1) // limit if total_count > 0 else 0
        skip = (page - 1) * limit
        
        # Paginated logs
        user_logs = await Log.find(query).sort("-created_at").skip(skip).limit(limit).to_list()
        
        # Get all detected entities for this user (from files they analyzed)
        user_entities = await DetectedEntity.find({
            "created_at": {"$gte": start_date}
        }).to_list()
        
        # Filter entities by checking logs for file operations
        file_operations = []
        network_operations = []
        analysis_operations = []
        
        for log in user_logs:
            safe_meta = sanitize_extra_data(log.extra_data) if log.extra_data else {}
            operation = {
                "id": str(log.id),
                "event_type": log.event_type,
                "message": log.message,
                "level": log.level,
                "timestamp": to_iso_utc(log.created_at),
                "timestamp_server": format_datetime_server(log.created_at),
                "source_ip": log.source_ip,
                "user_agent": log.user_agent,
                "metadata": safe_meta,
            }
            
            # Add file information if available
            if log.file_name:
                operation["file_name"] = log.file_name
                operation["file_size"] = log.file_size
                operation["file_type"] = log.file_type
                file_operations.append(operation)
            
            # Add network information if available
            if log.network_destination:
                operation["network_destination"] = log.network_destination
                operation["network_protocol"] = log.network_protocol
                network_operations.append(operation)
            
            # Analysis operations (from Analysis tab: text analysis, file analysis, policy applied)
            if log.event_type in ["analysis", "policy_applied", "file_analyzed", "entities_detected_no_policy_match"]:
                analysis_operations.append(operation)
        
        # Get unique file names
        unique_files = list(set([
            log.file_name for log in user_logs 
            if log.file_name
        ]))
        
        # Get network destinations
        unique_destinations = list(set([
            log.network_destination for log in user_logs 
            if log.network_destination
        ]))
        
        # Collect all policy IDs referenced in log metadata for name resolution
        all_policy_ids = set()
        for log in user_logs:
            meta = log.extra_data or {}
            ids = meta.get("matching_policy_ids") or []
            for pid in ids:
                try:
                    all_policy_ids.add(pid)
                except Exception:
                    pass
        policy_id_to_name = {}
        if all_policy_ids:
            from bson import ObjectId
            oids = []
            for pid in all_policy_ids:
                try:
                    oids.append(ObjectId(pid))
                except Exception:
                    pass
            if oids:
                policies = await Policy.find({"_id": {"$in": oids}}).to_list()
                for p in policies:
                    policy_id_to_name[str(p.id)] = p.name or str(p.id)
        
        def policy_names_for_log(log):
            meta = log.extra_data or {}
            ids = meta.get("matching_policy_ids") or []
            return [policy_id_to_name.get(pid, pid) for pid in ids]
        
        # Summary uses total count in period; per-type counts are for current page
        return {
            "user_id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role.value if getattr(user, "role", None) is not None else "regular",
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": get_current_time().isoformat(),
            "summary": {
                "total_operations": total_count,
                "file_operations": len(file_operations),
                "network_operations": len(network_operations),
                "analysis_operations": len(analysis_operations),
                "unique_files_analyzed": len(unique_files),
                "unique_network_destinations": len(unique_destinations)
            },
            "files_analyzed": unique_files,
            "network_destinations": unique_destinations,
            "operations": {
                "all": [
                    {
                        "id": str(log.id),
                        "event_type": log.event_type,
                        "message": log.message,
                        "timestamp": to_iso_utc(log.created_at),
                        "timestamp_server": format_datetime_server(log.created_at),
                        "source_ip": log.source_ip,
                        "source_user": log.source_user,
                        "file_name": log.file_name,
                        "network_destination": log.network_destination,
                        "metadata": sanitize_extra_data(log.extra_data) if log.extra_data else {},
                        "policy_names": policy_names_for_log(log)
                    }
                    for log in user_logs
                ],
                "file_operations": file_operations,
                "network_operations": network_operations,
                "analysis_operations": analysis_operations
            },
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user activities: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error fetching user activities: {str(e)}")