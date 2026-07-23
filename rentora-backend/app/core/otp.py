import random
from datetime import datetime, timedelta
from typing import Dict

_otp_store: Dict[str, dict] = {}

OTP_EXPIRE_MINUTES = 5


def generate_otp(phone: str) -> str:
    code = str(random.randint(100000, 999999))
    _otp_store[phone] = {
        "code": code,
        "expires_at": datetime.utcnow() + timedelta(minutes=OTP_EXPIRE_MINUTES),
    }
    return code


def verify_otp(phone: str, code: str) -> bool:
    entry = _otp_store.get(phone)
    if not entry:
        return False
    if datetime.utcnow() > entry["expires_at"]:
        del _otp_store[phone]
        return False
    if entry["code"] != code:
        return False
    del _otp_store[phone]
    return True