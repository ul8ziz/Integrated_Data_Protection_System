"""
API routes for alerts management
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.schemas.alerts import AlertResponse, AlertUpdate
from app.models.alerts import Alert, AlertStatus

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


@router.get("/", response_model=List[AlertResponse])
async def get_alerts(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get all alerts, optionally filtered by status and severity
    """
    try:
        query = db.query(Alert)
        
        if status:
            try:
                status_enum = AlertStatus(status)
                query = query.filter(Alert.status == status_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        if severity:
            from app.models.alerts import AlertSeverity
            try:
                severity_enum = AlertSeverity(severity)
                query = query.filter(Alert.severity == severity_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
        
        alerts = query.order_by(Alert.created_at.desc()).limit(limit).all()
        
        # Convert alerts to response format
        result = []
        for alert in alerts:
            try:
                alert_data = {
                    "id": alert.id,
                    "title": alert.title,
                    "description": alert.description,
                    "severity": alert.severity.value if alert.severity else "medium",
                    "status": alert.status.value if alert.status else "pending",
                    "source_ip": alert.source_ip,
                    "source_user": alert.source_user,
                    "source_device": alert.source_device,
                    "detected_entities": alert.detected_entities if alert.detected_entities else [],
                    "policy_id": alert.policy_id,
                    "action_taken": alert.action_taken,
                    "blocked": alert.blocked if alert.blocked is not None else False,
                    "created_at": alert.created_at,
                    "resolved_at": alert.resolved_at,
                    "resolved_by": alert.resolved_by
                }
                result.append(AlertResponse(**alert_data))
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
    alert_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific alert by ID
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertResponse.model_validate(alert)


@router.put("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: int,
    alert_update: AlertUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an alert (e.g., acknowledge or resolve)
    """
    try:
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        if alert_update.status:
            try:
                alert.status = AlertStatus(alert_update.status)
                if alert.status in [AlertStatus.RESOLVED, AlertStatus.FALSE_POSITIVE]:
                    alert.resolved_at = datetime.now()
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {alert_update.status}")
        
        if alert_update.resolved_by:
            alert.resolved_by = alert_update.resolved_by
        
        db.commit()
        db.refresh(alert)
        
        return AlertResponse.model_validate(alert)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating alert: {str(e)}")


@router.get("/stats/summary")
async def get_alert_stats(db: Session = Depends(get_db)):
    """
    Get alert statistics summary
    """
    try:
        total = db.query(Alert).count()
        pending = db.query(Alert).filter(Alert.status == AlertStatus.PENDING).count()
        resolved = db.query(Alert).filter(Alert.status == AlertStatus.RESOLVED).count()
        blocked = db.query(Alert).filter(Alert.blocked == True).count()
        
        return {
            "total": total,
            "pending": pending,
            "resolved": resolved,
            "blocked": blocked
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")

