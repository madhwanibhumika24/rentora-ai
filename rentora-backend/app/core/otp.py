import random
from datetime import datetime, timedelta
from typing import Dict

_otp_store: Dict[str, dict] = {}

OTP_EXPIRE_MINUTES = 10


def generate_otp(identifier: str) -> str:
    code = str(random.randint(100000, 999999))
    _otp_store[identifier] = {
        "code": code,
        "expires_at": datetime.utcnow() + timedelta(minutes=OTP_EXPIRE_MINUTES),
    }
    return code


def verify_otp(identifier: str, code: str) -> bool:
    entry = _otp_store.get(identifier)
    if not entry:
        return False
    if datetime.utcnow() > entry["expires_at"]:
        del _otp_store[identifier]
        return False
    if entry["code"] != code:
        return False
    del _otp_store[identifier]
    return True