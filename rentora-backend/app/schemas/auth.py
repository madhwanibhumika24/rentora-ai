from pydantic import BaseModel, EmailStr

from app.models.user import UserRole


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.tenant


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    otp: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str


class GoogleLoginRequest(BaseModel):
    credential: str
    role: UserRole = UserRole.tenant


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    role: UserRole