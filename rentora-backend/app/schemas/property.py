from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.models.room import RoomType


class PropertyCreate(BaseModel):
    name: str
    city: str
    address: str
    amenities: Optional[str] = None


class PropertyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    name: str
    city: str
    address: str
    amenities: Optional[str] = None
    created_at: datetime


class RoomCreate(BaseModel):
    room_type: RoomType = RoomType.double
    bed_count: int = 1
    rent_amount: float


class RoomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    property_id: int
    room_type: RoomType
    bed_count: int
    rent_amount: float
    is_available: bool