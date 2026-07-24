from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict

from app.models.due import DueStatus


class DueCreate(BaseModel):
    tenant_id: int
    category: str
    amount: float
    due_date: date


class DueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    category: str
    amount: float
    due_date: date
    status: DueStatus
    late_fee: float
    total_amount: float


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    due_id: int
    amount: float
    method: str
    transaction_id: Optional[str] = None
    paid_at: datetime


class OrderOut(BaseModel):
    # What we send back to the browser so it can open the Razorpay popup
    order_id: str
    amount: int
    currency: str
    key_id: str
    due_id: int


class VerifyPaymentRequest(BaseModel):
    # These three values come back from the Razorpay popup after the
    # tenant finishes paying. We use them to check the payment is real.
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str