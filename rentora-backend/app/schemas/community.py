from datetime import datetime
from pydantic import BaseModel, ConfigDict


class CommunityPostCreate(BaseModel):
    property_id: int
    text: str


class CommunityPostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    property_id: int
    author_id: int
    text: str
    created_at: datetime