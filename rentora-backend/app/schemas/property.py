from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.models.room import RoomType


class PropertyCreate(BaseModel):
    name: str
    city: str
    address: str
    amenities: Optional[str] = None
    # Both optional - only sent if the owner's building actually has
    # floors, or if they want to note a rough total room count up front.
    total_floors: Optional[int] = None
    total_rooms: Optional[int] = None


class PropertyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    name: str
    city: str
    address: str
    amenities: Optional[str] = None
    total_floors: Optional[int] = None
    total_rooms: Optional[int] = None
    created_at: datetime


class PropertyUpdate(BaseModel):
    # Everything here is optional - only the fields actually sent get
    # updated (e.g. fixing a typo in the city won't touch anything else).
    name: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    amenities: Optional[str] = None
    total_floors: Optional[int] = None
    total_rooms: Optional[int] = None


class RoomCreate(BaseModel):
    room_type: RoomType = RoomType.double
    bed_count: int = 1
    rent_amount: float
    # Both optional - only set if the owner's property has floors and/or
    # labels its rooms with a number.
    floor_number: Optional[int] = None
    room_number: Optional[str] = None


class RoomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    property_id: int
    room_type: RoomType
    bed_count: int
    rent_amount: float
    is_available: bool
    floor_number: Optional[int] = None
    room_number: Optional[str] = None


class PhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    property_id: int
    image_url: str
    created_at: datetime


class RuleCreate(BaseModel):
    text: str


class RuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    property_id: int
    text: str
    created_at: datetime