from typing import Optional
from pydantic import BaseModel


class CallRequestCreate(BaseModel):
    # Both optional: if phone is left blank we fall back to the tenant's
    # saved phone number (if they have one).
    phone: Optional[str] = None
    note: Optional[str] = None
