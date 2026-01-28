"""
Log and DetectedEntity models for MongoDB using Beanie
"""
from beanie import Document
from pydantic import Field
from typing import Optional, Dict, Any
from datetime import datetime
from app.utils.datetime_utils import get_current_time


class Log(Document):
    """Log model for activity tracking"""
    
    # Log information
    event_type: str = Field(..., max_length=100)  # analysis, block, alert, policy_change, etc.
    message: str
    level: str = Field(default="INFO", max_length=20)  # DEBUG, INFO, WARNING, ERROR
    
    # Source information
    source_ip: Optional[str] = Field(None, max_length=45)
    source_user: Optional[str] = Field(None, max_length=100)
    user_agent: Optional[str] = Field(None, max_length=255)
    
    # File information (for file analysis operations)
    file_name: Optional[str] = Field(None, max_length=500)
    file_size: Optional[int] = None
    file_type: Optional[str] = Field(None, max_length=50)
    
    # Network information (for network operations)
    network_destination: Optional[str] = Field(None, max_length=500)
    network_protocol: Optional[str] = Field(None, max_length=50)
    
    # Additional data
    extra_data: Optional[Dict[str, Any]] = None
    
    # Timestamp
    created_at: datetime = Field(default_factory=get_current_time)
    
    class Settings:
        name = "logs"  # Collection name
        indexes = [
            "event_type",
            "level",
            "created_at",
            "source_user",
            "file_name"
        ]
    
    def __repr__(self):
        return f"<Log(id={self.id}, event_type='{self.event_type}', level='{self.level}')>"


class DetectedEntity(Document):
    """DetectedEntity model for storing detected sensitive data"""
    
    # Entity information
    entity_type: str = Field(..., max_length=100)  # PERSON, PHONE_NUMBER, etc.
    value: str  # Encrypted value
    confidence: float  # Confidence score from Presidio
    
    # Location in text
    start_position: int
    end_position: int
    
    # Source information
    source_text_hash: Optional[str] = Field(None, max_length=64)  # SHA-256 hash of original text
    source_file: Optional[str] = Field(None, max_length=500)
    source_url: Optional[str] = Field(None, max_length=1000)
    
    # Action taken
    action: Optional[str] = Field(None, max_length=50)  # encrypted, anonymized, blocked, etc.
    
    # Relationships
    alert_id: Optional[str] = None  # Alert ID reference
    log_id: Optional[str] = None  # Log ID reference
    
    # Metadata
    created_at: datetime = Field(default_factory=get_current_time)
    
    class Settings:
        name = "detected_entities"  # Collection name
        indexes = [
            "entity_type",
            "alert_id",
            "log_id",
            "created_at"
        ]
    
    def __repr__(self):
        return f"<DetectedEntity(id={self.id}, entity_type='{self.entity_type}', confidence={self.confidence})>"
