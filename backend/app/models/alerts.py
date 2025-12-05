"""
Alert model for security notifications
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Enum, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class AlertStatus(enum.Enum):
    """Alert status enumeration"""
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class AlertSeverity(enum.Enum):
    """Alert severity enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Alert(Base):
    """Alert model for security notifications"""
    
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Alert information
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(Enum(AlertSeverity), nullable=False, default=AlertSeverity.MEDIUM)
    status = Column(Enum(AlertStatus), nullable=False, default=AlertStatus.PENDING)
    
    # Source information
    source_ip = Column(String(45), nullable=True)  # IPv6 support
    source_user = Column(String(100), nullable=True)
    source_device = Column(String(100), nullable=True)
    
    # Detected entities
    detected_entities = Column(JSON, nullable=True)  # List of detected sensitive data
    policy_id = Column(Integer, ForeignKey("policies.id"), nullable=True)
    
    # Action taken
    action_taken = Column(String(100), nullable=True)  # blocked, encrypted, anonymized, etc.
    blocked = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String(100), nullable=True)
    
    # Relationships
    policy = relationship("Policy")
    
    def __repr__(self):
        return f"<Alert(id={self.id}, title='{self.title}', severity={self.severity.value})>"

