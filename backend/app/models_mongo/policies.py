"""
Policy model for MongoDB using Beanie
"""
from beanie import Document
from pydantic import Field
from typing import List, Optional
from datetime import datetime


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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    
    class Settings:
        name = "policies"  # Collection name
        indexes = [
            "name",
            "enabled"
        ]
    
    def __repr__(self):
        return f"<Policy(id={self.id}, name='{self.name}', action='{self.action}')>"
