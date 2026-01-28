"""
API routes for monitoring and reports
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from typing import Dict, Any
from datetime import datetime, timedelta
from app.utils.datetime_utils import get_current_time
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
                    "created_at": log.created_at.isoformat(),
                    "metadata": log.extra_data
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


@router.get("/user-activities/{user_id}")
async def get_user_activities(
    user_id: str,
    days: int = 30,
    current_user = Depends(get_current_admin)  # Admin only
):
    """
    Get all activities for a specific user
    
    Returns:
    - All operations performed by the user
    - Files analyzed by the user
    - Files sent over network by the user
    - Detailed information for each operation
    """
    try:
        from datetime import datetime, timedelta
        from app.models_mongo.users import User
        
        # Verify user exists
        user = await User.get(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        start_date = get_current_time() - timedelta(days=days)
        
        # Get all logs for this user
        user_logs = await Log.find({
            "source_user": user.username,
            "created_at": {"$gte": start_date}
        }).sort("-created_at").to_list()
        
        # Get all detected entities for this user (from files they analyzed)
        user_entities = await DetectedEntity.find({
            "created_at": {"$gte": start_date}
        }).to_list()
        
        # Filter entities by checking logs for file operations
        file_operations = []
        network_operations = []
        analysis_operations = []
        
        for log in user_logs:
            operation = {
                "id": str(log.id),
                "event_type": log.event_type,
                "message": log.message,
                "level": log.level,
                "timestamp": log.created_at.isoformat(),
                "source_ip": log.source_ip,
                "user_agent": log.user_agent,
                "metadata": log.extra_data or {}
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
            
            # Analysis operations
            if log.event_type in ["analysis", "policy_applied", "file_analyzed"]:
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
        
        return {
            "user_id": str(user.id),
            "username": user.username,
            "email": user.email,
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": get_current_time().isoformat(),
            "summary": {
                "total_operations": len(user_logs),
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
                        "timestamp": log.created_at.isoformat(),
                        "source_ip": log.source_ip,
                        "file_name": log.file_name,
                        "network_destination": log.network_destination,
                        "metadata": log.extra_data or {}
                    }
                    for log in user_logs
                ],
                "file_operations": file_operations,
                "network_operations": network_operations,
                "analysis_operations": analysis_operations
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user activities: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error fetching user activities: {str(e)}")

