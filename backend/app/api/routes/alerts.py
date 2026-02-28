"""
API routes for alerts management - MongoDB version
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.schemas.alerts import AlertResponse, AlertUpdate
from app.models_mongo.alerts import Alert, AlertStatus, AlertSeverity
from app.models_mongo.policies import Policy
from app.api.dependencies import get_current_admin

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


@router.get("/", response_model=Dict[str, Any])
async def get_alerts(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user = Depends(get_current_admin)  # Admin only
):
    """
    Get all alerts with pagination, optionally filtered by status and severity
    
    Query parameters:
    - status: Filter by status
    - severity: Filter by severity
    - page: Page number (default: 1)
    - limit: Items per page (default: 10, max: 100)
    """
    try:
        query = {}
        
        if status:
            try:
                status_enum = AlertStatus(status)
                query["status"] = status_enum.value
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        if severity:
            try:
                severity_enum = AlertSeverity(severity)
                query["severity"] = severity_enum.value
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
        
        # Calculate pagination
        skip = (page - 1) * limit
        
        # Get total count
        if query:
            total_count = await Alert.find(query).count()
            alerts = await Alert.find(query).sort("-created_at").skip(skip).limit(limit).to_list()
        else:
            total_count = await Alert.find({}).count()
            alerts = await Alert.find({}).sort("-created_at").skip(skip).limit(limit).to_list()
        
        # Convert alerts to response format
        result = []
        for alert in alerts:
            try:
                # Get policy name if policy_id exists
                policy_name = None
                if alert.policy_id:
                    try:
                        from beanie import PydanticObjectId
                        policy = await Policy.get(PydanticObjectId(alert.policy_id))
                        if policy and not policy.is_deleted:
                            policy_name = policy.name
                    except Exception:
                        # Policy not found or deleted, policy_name will remain None
                        pass
                
                # Clean up title - remove policy name from title if it exists
                clean_title = alert.title
                if policy_name and f"Policy: {policy_name}" in clean_title:
                    clean_title = clean_title.replace(f"Policy: {policy_name}", "").replace(" - ", "").strip()
                    if clean_title.endswith("-"):
                        clean_title = clean_title[:-1].strip()
                
                result.append(AlertResponse(
                    id=str(alert.id),
                    title=clean_title,
                    description=alert.description,
                    severity=alert.severity.value if alert.severity else "medium",
                    status=alert.status.value if alert.status else "pending",
                    source_ip=alert.source_ip,
                    source_user=alert.source_user,
                    source_device=alert.source_device,
                    detected_entities=alert.detected_entities if alert.detected_entities else [],
                    policy_id=str(alert.policy_id) if alert.policy_id else None,
                    policy_name=policy_name,  # Include policy name from database
                    action_taken=alert.action_taken,
                    blocked=alert.blocked if alert.blocked is not None else False,
                    created_at=alert.created_at,
                    resolved_at=alert.resolved_at,
                    resolved_by=alert.resolved_by
                ))
            except Exception as e:
                # Skip problematic alerts and log error
                import logging
                logging.getLogger(__name__).error(f"Error processing alert {alert.id}: {e}")
                continue
        
        # Calculate pagination metadata
        total_pages = (total_count + limit - 1) // limit if total_count > 0 else 0
        
        return {
            "items": result,
            "total": total_count,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error fetching alerts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching alerts: {str(e)}")


@router.get("/recent", response_model=Dict[str, Any])
async def get_recent_alerts(
    since: Optional[str] = Query(None, description="ISO 8601 datetime; alerts created after this time"),
    limit: int = Query(50, ge=1, le=100),
    current_user = Depends(get_current_admin)  # Admin only
):
    """
    Get alerts created after a given time (for admin real-time notifications).
    If 'since' is omitted, defaults to 24 hours ago.
    """
    try:
        from datetime import timedelta
        from dateutil import parser as date_parser
        from app.utils.datetime_utils import get_current_time

        if since:
            try:
                since_dt = date_parser.isoparse(since)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid 'since' format; use ISO 8601")
        else:
            since_dt = get_current_time() - timedelta(hours=24)

        query = {"created_at": {"$gt": since_dt}}
        alerts = await Alert.find(query).sort("-created_at").limit(limit).to_list()

        result = []
        for alert in alerts:
            try:
                policy_name = None
                if alert.policy_id:
                    try:
                        from beanie import PydanticObjectId
                        policy = await Policy.get(PydanticObjectId(alert.policy_id))
                        if policy and not getattr(policy, "is_deleted", False):
                            policy_name = policy.name
                    except Exception:
                        pass

                result.append(AlertResponse(
                    id=str(alert.id),
                    title=alert.title,
                    description=alert.description,
                    severity=alert.severity.value if alert.severity else "medium",
                    status=alert.status.value if alert.status else "pending",
                    source_ip=alert.source_ip,
                    source_user=alert.source_user,
                    source_device=alert.source_device,
                    detected_entities=alert.detected_entities if alert.detected_entities else [],
                    policy_id=str(alert.policy_id) if alert.policy_id else None,
                    policy_name=policy_name,
                    action_taken=alert.action_taken,
                    blocked=alert.blocked if alert.blocked is not None else False,
                    created_at=alert.created_at,
                    resolved_at=alert.resolved_at,
                    resolved_by=alert.resolved_by
                ))
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error processing alert {alert.id}: {e}")
                continue

        return {
            "items": result,
            "count": len(result)
        }
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error fetching recent alerts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching recent alerts: {str(e)}")


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    current_user = Depends(get_current_admin)  # Admin only
):
    """
    Get a specific alert by ID
    """
    try:
        alert = await Alert.get(alert_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Get policy name if policy_id exists
    policy_name = None
    if alert.policy_id:
        try:
            from beanie import PydanticObjectId
            policy = await Policy.get(PydanticObjectId(alert.policy_id))
            if policy and not policy.is_deleted:
                policy_name = policy.name
        except Exception:
            pass
    
    # Title is now the policy name directly, no need to clean
    return AlertResponse(
        id=str(alert.id),
        title=alert.title,
        description=alert.description,
        severity=alert.severity.value if alert.severity else "medium",
        status=alert.status.value if alert.status else "pending",
        source_ip=alert.source_ip,
        source_user=alert.source_user,
        source_device=alert.source_device,
        detected_entities=alert.detected_entities if alert.detected_entities else [],
        policy_id=str(alert.policy_id) if alert.policy_id else None,
        policy_name=policy_name,
        action_taken=alert.action_taken,
        blocked=alert.blocked if alert.blocked is not None else False,
        created_at=alert.created_at,
        resolved_at=alert.resolved_at,
        resolved_by=alert.resolved_by
    )


@router.put("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: str,
    alert_update: AlertUpdate,
    current_user = Depends(get_current_admin)  # Admin only
):
    """
    Update an alert (e.g., acknowledge or resolve)
    """
    try:
        try:
            alert = await Alert.get(alert_id)
        except Exception:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        if alert_update.status:
            try:
                alert.status = AlertStatus(alert_update.status)
                if alert.status in [AlertStatus.RESOLVED, AlertStatus.FALSE_POSITIVE]:
                    from app.utils.datetime_utils import get_current_time
                    alert.resolved_at = get_current_time()
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {alert_update.status}")
        
        if alert_update.resolved_by:
            alert.resolved_by = alert_update.resolved_by
        
        await alert.save()
        
        # Get policy name if policy_id exists
        policy_name = None
        if alert.policy_id:
            try:
                from beanie import PydanticObjectId
                policy = await Policy.get(PydanticObjectId(alert.policy_id))
                if policy and not policy.is_deleted:
                    policy_name = policy.name
            except Exception:
                pass
        
        # Title is now the policy name directly, no need to clean
        return AlertResponse(
            id=str(alert.id),
            title=alert.title,
            description=alert.description,
            severity=alert.severity.value if alert.severity else "medium",
            status=alert.status.value if alert.status else "pending",
            source_ip=alert.source_ip,
            source_user=alert.source_user,
            source_device=alert.source_device,
            detected_entities=alert.detected_entities if alert.detected_entities else [],
            policy_id=str(alert.policy_id) if alert.policy_id else None,
            policy_name=policy_name,
            action_taken=alert.action_taken,
            blocked=alert.blocked if alert.blocked is not None else False,
            created_at=alert.created_at,
            resolved_at=alert.resolved_at,
            resolved_by=alert.resolved_by
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating alert: {str(e)}")


@router.get("/stats/summary")
async def get_alert_stats(
    current_user = Depends(get_current_admin)  # Admin only
):
    """
    Get alert statistics summary
    """
    try:
        total = await Alert.find({}).count()
        pending = await Alert.find({"status": AlertStatus.PENDING.value}).count()
        resolved = await Alert.find({"status": AlertStatus.RESOLVED.value}).count()
        blocked = await Alert.find({"blocked": True}).count()
        
        return {
            "total": total,
            "pending": pending,
            "resolved": resolved,
            "blocked": blocked
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")
