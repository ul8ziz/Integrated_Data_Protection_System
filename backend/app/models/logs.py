"""
Log and DetectedEntity models for activity tracking
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Log(Base):
    """Log model for activity tracking"""
    
    __tablename__ = "logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Log information
    event_type = Column(String(100), nullable=False)  # analysis, block, alert, policy_change, etc.
    message = Column(Text, nullable=False)
    level = Column(String(20), nullable=False, default="INFO")  # DEBUG, INFO, WARNING, ERROR
    
    # Source information
    source_ip = Column(String(45), nullable=True)
    source_user = Column(String(100), nullable=True)
    user_agent = Column(String(255), nullable=True)
    
    # Additional data
    extra_data = Column(JSON, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    def __repr__(self):
        return f"<Log(id={self.id}, event_type='{self.event_type}', level='{self.level}')>"


class DetectedEntity(Base):
    """DetectedEntity model for storing detected sensitive data"""
    
    __tablename__ = "detected_entities"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Entity information
    entity_type = Column(String(100), nullable=False)  # PERSON, PHONE_NUMBER, etc.
    value = Column(Text, nullable=False)  # Encrypted value
    confidence = Column(Float, nullable=False)  # Confidence score from Presidio
    
    # Location in text
    start_position = Column(Integer, nullable=False)
    end_position = Column(Integer, nullable=False)
    
    # Source information
    source_text_hash = Column(String(64), nullable=True)  # SHA-256 hash of original text
    source_file = Column(String(500), nullable=True)
    source_url = Column(String(1000), nullable=True)
    
    # Action taken
    action = Column(String(50), nullable=True)  # encrypted, anonymized, blocked, etc.
    
    # Relationships
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=True)
    log_id = Column(Integer, ForeignKey("logs.id"), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    def __repr__(self):
        return f"<DetectedEntity(id={self.id}, entity_type='{self.entity_type}', confidence={self.confidence})>"

