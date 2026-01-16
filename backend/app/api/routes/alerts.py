"""
API routes for alerts management - MongoDB version
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from app.schemas.alerts import AlertResponse, AlertUpdate
from app.models_mongo.alerts import Alert, AlertStatus, AlertSeverity
from app.api.dependencies import get_current_admin

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


@router.get("/", response_model=List[AlertResponse])
async def get_alerts(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    current_user = Depends(get_current_admin)  # Admin only
):
    """
    Get all alerts, optionally filtered by status and severity
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
        
        if query:
            alerts = await Alert.find(query).sort("-created_at").limit(limit).to_list()
        else:
            alerts = await Alert.find({}).sort("-created_at").limit(limit).to_list()
        
        # Convert alerts to response format
        result = []
        for alert in alerts:
            try:
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
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error fetching alerts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching alerts: {str(e)}")


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
                    alert.resolved_at = datetime.utcnow()
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {alert_update.status}")
        
        if alert_update.resolved_by:
            alert.resolved_by = alert_update.resolved_by
        
        await alert.save()
        
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
