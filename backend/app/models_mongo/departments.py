"""
Department model for MongoDB using Beanie
"""
from beanie import Document
from pydantic import Field
from typing import Optional
from datetime import datetime
from app.utils.datetime_utils import get_current_time


class Department(Document):
    """Department model for organization structure"""

    name: str = Field(..., max_length=255)
    description: Optional[str] = None

    created_at: datetime = Field(default_factory=get_current_time)
    updated_at: Optional[datetime] = None

    class Settings:
        name = "departments"
        indexes = [
            "name",
            "created_at"
        ]

    def __repr__(self):
        return f"<Department(id={self.id}, name='{self.name}')>"
