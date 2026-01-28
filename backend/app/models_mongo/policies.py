"""
Policy model for MongoDB using Beanie
"""
from beanie import Document
from pydantic import Field
from typing import List, Optional
from datetime import datetime
from app.utils.datetime_utils import get_current_time


class Policy(Document):
    """Policy model for defining data protection rules"""
    
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    
    # Policy configuration
    entity_types: List[str] = Field(...)  # List of entity types to monitor
    action: str = Field(..., max_length=50)  # block, alert, encrypt, anonymize
    severity: str = Field(default="medium", max_length=20)  # low, medium, high, critical
    
    # Scope
    enabled: bool = Field(default=True)
    apply_to_network: bool = Field(default=True)
    apply_to_devices: bool = Field(default=True)
    apply_to_storage: bool = Field(default=True)
    
    # Compliance
    gdpr_compliant: bool = Field(default=False)
    hipaa_compliant: bool = Field(default=False)
    
    # Metadata
    created_at: datetime = Field(default_factory=get_current_time)
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    is_deleted: bool = Field(default=False)  # Soft delete flag
    
    class Settings:
        name = "policies"  # Collection name
        indexes = [
            "name",
            "enabled",
            "is_deleted"
        ]
    
    def __repr__(self):
        return f"<Policy(id={self.id}, name='{self.name}', action='{self.action}')>"
