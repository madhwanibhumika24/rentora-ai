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