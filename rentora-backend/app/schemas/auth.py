from typing import Optional
from pydantic import BaseModel

from app.models.user import UserRole


class OtpRequest(BaseModel):
    phone: str


class OtpVerify(BaseModel):
    phone: str
    otp: str
    name: Optional[str] = None
    role: UserRole = UserRole.tenant


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    role: UserRole