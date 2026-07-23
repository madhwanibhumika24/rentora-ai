from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.models.complaint import ComplaintStatus


class ComplaintCreate(BaseModel):
    property_id: int
    category: str
    description: Optional[str] = None
    photo_url: Optional[str] = None


class ComplaintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    property_id: int
    category: str
    description: Optional[str] = None
    photo_url: Optional[str] = None
    status: ComplaintStatus
    created_at: datetime


class ComplaintStatusUpdate(BaseModel):
    status: ComplaintStatus