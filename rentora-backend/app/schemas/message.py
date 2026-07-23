from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class MessageCreate(BaseModel):
    receiver_id: int
    property_id: Optional[int] = None
    text: str


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sender_id: int
    receiver_id: int
    property_id: Optional[int] = None
    text: str
    sent_at: datetime