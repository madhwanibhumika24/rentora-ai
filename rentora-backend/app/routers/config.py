from fastapi import APIRouter

from app.config import settings

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/public")
def get_public_config():
    # Only send values that are safe to show in the browser.
    # razorpay_key_id is public by design (it identifies the account, not a secret).
    # razorpay_key_secret must NEVER be sent to the frontend.
    return {
        "google_client_id": settings.google_client_id,
        "razorpay_key_id": settings.razorpay_key_id,
    }
