"""
Schemas for text analysis API
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.utils.datetime_utils import get_current_time


class DetectedEntitySchema(BaseModel):
    """Schema for detected entity"""
    entity_type: str
    start: int
    end: int
    score: float
    value: str
    
    class Config:
        from_attributes = True


class AnalysisRequest(BaseModel):
    """Request schema for text analysis"""
    text: str = Field(..., description="Text to analyze for sensitive data")
    language: Optional[str] = Field(None, description="Language code (default: configured language)")
    source_ip: Optional[str] = Field(None, description="Source IP address")
    source_user: Optional[str] = Field(None, description="Source user")
    source_device: Optional[str] = Field(None, description="Source device")
    apply_policies: bool = Field(True, description="Whether to apply policies automatically")


class AppliedPolicySchema(BaseModel):
    """Schema for applied policy information"""
    id: str
    name: str
    action: str
    severity: str
    entity_types: List[str]
    matched_entities: List[str]
    matched_count: int


class AnalysisResponse(BaseModel):
    """Response schema for text analysis"""
    sensitive_data_detected: bool
    detected_entities: List[DetectedEntitySchema] = []
    actions_taken: List[str] = []
    blocked: bool = False
    alert_created: bool = False
    policies_matched: bool = False
    applied_policies: List[AppliedPolicySchema] = []
    timestamp: datetime = Field(default_factory=get_current_time)
    
    class Config:
        from_attributes = True

