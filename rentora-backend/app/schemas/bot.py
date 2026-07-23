from typing import List, Optional
from pydantic import BaseModel


class BotMessageRequest(BaseModel):
    intent: str
    text: Optional[str] = None


class BotMessageResponse(BaseModel):
    reply: str
    options: List[str] = []