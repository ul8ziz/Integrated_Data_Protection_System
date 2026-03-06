"""
Schemas for alerts API
"""
from pydantic import BaseModel, Field, field_serializer
from typing import List, Optional, Dict, Any
from datetime import datetime


def _datetime_to_iso_utc(dt: Optional[datetime]) -> Optional[str]:
    """Serialize datetime to ISO 8601 with Z so frontend parses as UTC and shows local time."""
    if dt is None:
        return None
    from datetime import timezone
    if getattr(dt, "tzinfo", None) is None:
        dt = dt.replace(tzinfo=timezone.utc)
    utc_dt = dt.astimezone(timezone.utc)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class AlertResponse(BaseModel):
    """Schema for alert response"""
    id: str  # MongoDB uses ObjectId (string)
    title: str
    description: Optional[str]
    severity: str
    status: str
    source_ip: Optional[str]
    source_user: Optional[str]
    source_device: Optional[str]
    detected_entities: Optional[List[Dict[str, Any]]]
    policy_id: Optional[str] = None  # MongoDB uses ObjectId (string)
    policy_name: Optional[str] = None  # Policy name from database (if policy exists)
    attachment_names: Optional[List[str]] = None  # File names when violation is from email with attachments
    action_taken: Optional[str]
    blocked: bool
    created_at: datetime
    created_at_server: Optional[str] = None  # Formatted in server timezone for display
    resolved_at: Optional[datetime]
    resolved_by: Optional[str]
    extra_data: Optional[Dict[str, Any]] = None  # e.g. {"to": ["a@x.com"]} for email alerts

    @field_serializer("created_at", "resolved_at")
    def serialize_datetime_iso_utc(self, dt: Optional[datetime]) -> Optional[str]:
        return _datetime_to_iso_utc(dt)
    
    class Config:
        from_attributes = True


class AlertUpdate(BaseModel):
    """Schema for updating an alert"""
    status: Optional[str] = Field(None, description="New status: pending, acknowledged, resolved, false_positive")
    resolved_by: Optional[str] = Field(None, description="User who resolved the alert")

