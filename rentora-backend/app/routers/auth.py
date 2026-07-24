from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

from app.database import get_db
from app.config import settings
from app.models.user import User
from app.schemas.auth import (
    SignupRequest,
    VerifyEmailRequest,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    GoogleLoginRequest,
    TokenResponse,
)
from app.core.otp import generate_otp, verify_otp
from app.core.security import create_access_token, hash_password, verify_password
from app.services.email import send_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup")
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_email_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    otp = generate_otp(payload.email)
    sent = send_email(
        payload.email,
        "Verify your Rentora account",
        f"Your verification code is {otp}. It expires in 10 minutes.",
    )

    if sent:
        return {"message": "Account created. Check your email for a verification code."}
    return {"message": "Account created. (Dev mode - no email configured)", "otp": otp}


@router.post("/verify-email", response_model=TokenResponse)
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)):
    if not verify_otp(payload.email, payload.otp):
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    user = db.query(User).filter(User.email == payload.email).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Account not found")

    user.is_email_verified = True
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return TokenResponse(access_token=token, user_id=user.id, role=user.role)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or user.password_hash is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_email_verified:
        raise HTTPException(status_code=403, detail="Please verify your email first")

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return TokenResponse(access_token=token, user_id=user.id, role=user.role)


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None:
        # Don't reveal whether the email is registered
        return {"message": "If that email is registered, a reset code has been sent."}

    otp = generate_otp("reset:" + payload.email)
    sent = send_email(
        payload.email,
        "Reset your Rentora password",
        f"Your password reset code is {otp}. It expires in 10 minutes.",
    )

    if sent:
        return {"message": "If that email is registered, a reset code has been sent."}
    return {"message": "Dev mode - no email configured", "otp": otp}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    if not verify_otp("reset:" + payload.email, payload.otp):
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    user = db.query(User).filter(User.email == payload.email).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Account not found")

    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password reset successfully. You can now log in."}


@router.post("/google", response_model=TokenResponse)
def google_login(payload: GoogleLoginRequest, db: Session = Depends(get_db)):
    try:
        idinfo = google_id_token.verify_oauth2_token(
            payload.credential, google_requests.Request(), settings.google_client_id
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Google token")

    email = idinfo.get("email")
    name = idinfo.get("name", "New user")
    google_id = idinfo.get("sub")

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(
            name=name,
            email=email,
            google_id=google_id,
            role=payload.role,
            is_email_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif user.google_id is None:
        user.google_id = google_id
        user.is_email_verified = True
        db.commit()
        db.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return TokenResponse(access_token=token, user_id=user.id, role=user.role)