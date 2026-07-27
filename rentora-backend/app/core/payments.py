import razorpay

from app.config import settings


def get_razorpay_client():
    """
    Returns a Razorpay client if keys are set in .env, otherwise None.
    Shared by both the rent-due payment flow (dues.py) and the booking
    token-payment flow (tenant.py), so there's only one place that reads
    the keys - keeping a client with no keys set means the app still
    works with the simple "dev mode" instant-pay button everywhere.
    """
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        return None
    return razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))
