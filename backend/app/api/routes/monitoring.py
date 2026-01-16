"""
API routes for monitoring and reports
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Dict, Any
from datetime import datetime, timedelta
from app.models_mongo.logs import Log, DetectedEntity
from app.models_mongo.alerts import Alert
from app.models_mongo.policies import Policy
from app.services.mydlp_service import MyDLPService
from app.services.email_monitoring_service import EmailMonitoringService
from app.api.dependencies import get_current_admin, get_optional_user

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
        "timestamp": datetime.now().isoformat()
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
        start_date = datetime.now() - timedelta(days=days)
        
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
    current_user = Depends(get_current_admin)  # Admin only
):
    """
    Get logs report
    """
    try:
        query = {}
        if event_type:
            query["event_type"] = event_type
        if level:
            query["level"] = level
        
        if query:
            logs = await Log.find(query).sort("-created_at").limit(limit).to_list()
        else:
            logs = await Log.find({}).sort("-created_at").limit(limit).to_list()
        
        return {
            "count": len(logs),
            "logs": [
                {
                    "id": str(log.id),
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
        "attachments": ["file1.pdf"],  # optional
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
                    "created_at": log.created_at.isoformat(),
                    "email_data": log.extra_data
                }
                for log in logs
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching email logs: {str(e)}")

