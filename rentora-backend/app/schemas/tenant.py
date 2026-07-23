from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict

from app.models.booking import BookingStatus


class BookingCreate(BaseModel):
    room_id: int
    move_in_date: Optional[date] = None


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    room_id: int
    status: BookingStatus
    move_in_date: Optional[date] = None
    created_at: datetime