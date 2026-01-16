"""
Alert model for MongoDB using Beanie
"""
from beanie import Document
from pydantic import Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class AlertStatus(str, Enum):
    """Alert status enumeration"""
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class AlertSeverity(str, Enum):
    """Alert severity enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Alert(Document):
    """Alert model for security notifications"""
    
    # Alert information
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    severity: AlertSeverity = Field(default=AlertSeverity.MEDIUM)
    status: AlertStatus = Field(default=AlertStatus.PENDING)
    
    # Source information
    source_ip: Optional[str] = Field(None, max_length=45)  # IPv6 support
    source_user: Optional[str] = Field(None, max_length=100)
    source_device: Optional[str] = Field(None, max_length=100)
    
    # Detected entities
    detected_entities: Optional[List[Dict[str, Any]]] = None  # List of detected sensitive data
    policy_id: Optional[str] = None  # Policy ID reference
    
    # Action taken
    action_taken: Optional[str] = Field(None, max_length=100)  # blocked, encrypted, anonymized, etc.
    blocked: bool = Field(default=False)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    
    class Settings:
        name = "alerts"  # Collection name
        indexes = [
            "status",
            "severity",
            "created_at",
            "policy_id"
        ]
    
    def __repr__(self):
        return f"<Alert(id={self.id}, title='{self.title}', severity={self.severity.value})>"
