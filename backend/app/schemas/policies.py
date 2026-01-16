"""
Schemas for policy management API
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class PolicyCreate(BaseModel):
    """Schema for creating a policy"""
    name: str = Field(..., description="Policy name")
    description: Optional[str] = Field(None, description="Policy description")
    entity_types: List[str] = Field(..., description="List of entity types to monitor")
    action: str = Field(..., description="Action to take: block, alert, encrypt, anonymize")
    severity: str = Field("medium", description="Severity level: low, medium, high, critical")
    enabled: bool = Field(True, description="Whether policy is enabled")
    apply_to_network: bool = Field(True, description="Apply to network traffic")
    apply_to_devices: bool = Field(True, description="Apply to device transfers")
    apply_to_storage: bool = Field(True, description="Apply to storage operations")
    gdpr_compliant: bool = Field(False, description="GDPR compliance flag")
    hipaa_compliant: bool = Field(False, description="HIPAA compliance flag")
    created_by: Optional[str] = Field(None, description="User who created the policy")


class PolicyUpdate(BaseModel):
    """Schema for updating a policy"""
    name: Optional[str] = None
    description: Optional[str] = None
    entity_types: Optional[List[str]] = None
    action: Optional[str] = None
    severity: Optional[str] = None
    enabled: Optional[bool] = None
    apply_to_network: Optional[bool] = None
    apply_to_devices: Optional[bool] = None
    apply_to_storage: Optional[bool] = None
    gdpr_compliant: Optional[bool] = None
    hipaa_compliant: Optional[bool] = None


class PolicyResponse(BaseModel):
    """Schema for policy response"""
    id: str  # MongoDB uses ObjectId (string)
    name: str
    description: Optional[str]
    entity_types: List[str]
    action: str
    severity: str
    enabled: bool
    apply_to_network: bool
    apply_to_devices: bool
    apply_to_storage: bool
    gdpr_compliant: bool
    hipaa_compliant: bool
    created_at: datetime
    updated_at: Optional[datetime]
    created_by: Optional[str]
    
    class Config:
        from_attributes = True

