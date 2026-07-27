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
    property_id: Optional[int] = None
    property_name: Optional[str] = None
    city: Optional[str] = None
    room_type: Optional[str] = None
    rent_amount: Optional[float] = None
    token_amount: Optional[float] = None
    token_paid: bool = False


class BookingStatusUpdate(BaseModel):
    status: BookingStatus


class BookingOrderOut(BaseModel):
    # What the browser needs to open the Razorpay popup for a booking's
    # deposit payment - same shape as dues' OrderOut, plus the room it's
    # for and the deposit amount so the frontend can show it before paying.
    order_id: str
    amount: int
    currency: str
    key_id: str
    room_id: int
    token_amount: float


class BookingVerifyRequest(BaseModel):
    room_id: int
    move_in_date: Optional[date] = None
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str