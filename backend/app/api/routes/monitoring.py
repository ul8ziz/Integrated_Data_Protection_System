"""
API routes for monitoring and reports
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime, timedelta
from app.database import get_db
from app.models.logs import Log, DetectedEntity
from app.models.alerts import Alert
from app.models.policies import Policy
from app.services.mydlp_service import MyDLPService
from app.services.email_monitoring_service import EmailMonitoringService

router = APIRouter(prefix="/api/monitoring", tags=["Monitoring"])

mydlp_service = MyDLPService()
email_monitoring = EmailMonitoringService()


@router.get("/status")
async def get_system_status():
    """
    Get system status and component health
    """
    return {
        "status": "operational",
        "presidio": {
            "enabled": True,
            "status": "operational"
        },
        "mydlp": {
            "enabled": mydlp_service.is_enabled(),
            "status": "operational" if mydlp_service.is_enabled() else "disabled",
            "is_localhost": mydlp_service.is_local() if mydlp_service.is_enabled() else False
        },
        "timestamp": datetime.now().isoformat()
    }


@router.post("/traffic")
async def monitor_traffic(
    traffic_data: Dict[str, Any],
    db: Session = Depends(get_db)
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
    db: Session = Depends(get_db)
):
    """
    Get summary report for the last N days
    """
    try:
        start_date = datetime.now() - timedelta(days=days)
        
        # Count logs
        total_logs = db.query(Log).filter(Log.created_at >= start_date).count()
        
        # Count detected entities
        total_entities = db.query(DetectedEntity).filter(
            DetectedEntity.created_at >= start_date
        ).count()
        
        # Count alerts
        total_alerts = db.query(Alert).filter(Alert.created_at >= start_date).count()
        blocked_count = db.query(Alert).filter(
            Alert.created_at >= start_date,
            Alert.blocked == True
        ).count()
        
        # Count policies
        active_policies = db.query(Policy).filter(Policy.enabled == True).count()
        
        # Entity type breakdown
        entity_types = db.query(DetectedEntity.entity_type).filter(
            DetectedEntity.created_at >= start_date
        ).all()
        entity_type_counts = {}
        for (entity_type,) in entity_types:
            entity_type_counts[entity_type] = entity_type_counts.get(entity_type, 0) + 1
        
        return {
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": datetime.now().isoformat(),
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
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get logs report
    """
    try:
        query = db.query(Log)
        
        if event_type:
            query = query.filter(Log.event_type == event_type)
        if level:
            query = query.filter(Log.level == level)
        
        logs = query.order_by(Log.created_at.desc()).limit(limit).all()
        
        return {
            "count": len(logs),
            "logs": [
                {
                    "id": log.id,
                    "event_type": log.event_type,
                    "message": log.message,
                    "level": log.level,
                    "source_ip": log.source_ip,
                    "source_user": log.source_user,
                    "created_at": log.created_at.isoformat(),
                    "metadata": log.extra_data
                }
                for log in logs
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching logs: {str(e)}")


@router.post("/email")
async def monitor_email(
    email_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Monitor and analyze email for sensitive data
    
    This endpoint receives email data and analyzes it for sensitive information.
    If sensitive data is detected, the email may be blocked based on policies.
    
    Request body:
    {
        "from": "sender@example.com",
        "to": ["recipient@example.com"],
        "subject": "Email subject",
        "body": "Email body text",
        "attachments": ["file1.pdf"],  # optional
        "source_ip": "127.0.0.1",  # optional, defaults to 127.0.0.1
        "source_user": "user@example.com"  # optional
    }
    """
    try:
        result = email_monitoring.analyze_email(db=db, email_data=email_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error monitoring email: {str(e)}")


@router.get("/email/statistics")
async def get_email_statistics(
    days: int = 7,
    db: Session = Depends(get_db)
):
    """
    Get email monitoring statistics
    
    Returns statistics about emails analyzed, blocked, and detected entities.
    """
    try:
        stats = email_monitoring.get_email_statistics(db=db, days=days)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting email statistics: {str(e)}")


@router.get("/email/logs")
async def get_email_logs(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get email monitoring logs
    
    Returns recent email analysis logs.
    """
    try:
        logs = db.query(Log).filter(
            Log.event_type == "email_received"
        ).order_by(Log.created_at.desc()).limit(limit).all()
        
        return {
            "count": len(logs),
            "logs": [
                {
                    "id": log.id,
                    "message": log.message,
                    "level": log.level,
                    "source_ip": log.source_ip,
                    "source_user": log.source_user,
                    "created_at": log.created_at.isoformat(),
                    "email_data": log.extra_data
                }
                for log in logs
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching email logs: {str(e)}")

