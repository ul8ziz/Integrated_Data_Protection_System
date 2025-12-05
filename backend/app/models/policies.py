"""
Policy model for data protection rules
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.database import Base


class Policy(Base):
    """Policy model for defining data protection rules"""
    
    __tablename__ = "policies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Policy configuration
    entity_types = Column(JSON, nullable=False)  # List of entity types to monitor
    action = Column(String(50), nullable=False)  # block, alert, encrypt, anonymize
    severity = Column(String(20), nullable=False, default="medium")  # low, medium, high, critical
    
    # Scope
    enabled = Column(Boolean, default=True)
    apply_to_network = Column(Boolean, default=True)
    apply_to_devices = Column(Boolean, default=True)
    apply_to_storage = Column(Boolean, default=True)
    
    # Compliance
    gdpr_compliant = Column(Boolean, default=False)
    hipaa_compliant = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(100), nullable=True)
    
    def __repr__(self):
        return f"<Policy(id={self.id}, name='{self.name}', action='{self.action}')>"

