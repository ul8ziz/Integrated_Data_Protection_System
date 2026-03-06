"""
Schemas for departments API
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DepartmentCreate(BaseModel):
    """Schema for creating a department"""
    name: str = Field(..., max_length=255, description="Department name")
    description: Optional[str] = Field(None, description="Department description")


class DepartmentUpdate(BaseModel):
    """Schema for updating a department"""
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None


class DepartmentResponse(BaseModel):
    """Schema for department response"""
    id: str
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
