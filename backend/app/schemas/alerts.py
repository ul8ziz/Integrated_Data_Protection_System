"""
Schemas for alerts API
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


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
    policy_id: Optional[str]  # MongoDB uses ObjectId (string)
    action_taken: Optional[str]
    blocked: bool
    created_at: datetime
    resolved_at: Optional[datetime]
    resolved_by: Optional[str]
    
    class Config:
        from_attributes = True


class AlertUpdate(BaseModel):
    """Schema for updating an alert"""
    status: Optional[str] = Field(None, description="New status: pending, acknowledged, resolved, false_positive")
    resolved_by: Optional[str] = Field(None, description="User who resolved the alert")

