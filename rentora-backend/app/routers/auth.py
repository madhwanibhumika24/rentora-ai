from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import OtpRequest, OtpVerify, TokenResponse
from app.core.otp import generate_otp, verify_otp
from app.core.security import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/request-otp")
def request_otp(payload: OtpRequest):
    code = generate_otp(payload.phone)
    # TODO: send `code` via an SMS gateway (Twilio/MSG91) instead of returning it directly.
    # Returned here only so the flow is testable before a gateway is wired up.
    return {"message": "OTP sent", "otp": code}


@router.post("/verify-otp", response_model=TokenResponse)
def verify_otp_endpoint(payload: OtpVerify, db: Session = Depends(get_db)):
    if not verify_otp(payload.phone, payload.otp):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    user = db.query(User).filter(User.phone == payload.phone).first()
    if user is None:
        user = User(
            name=payload.name or "New user",
            phone=payload.phone,
            role=payload.role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return TokenResponse(access_token=token, user_id=user.id, role=user.role)