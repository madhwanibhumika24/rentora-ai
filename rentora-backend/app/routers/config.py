from fastapi import APIRouter

from app.config import settings

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/public")
def get_public_config():
    return {"google_client_id": settings.google_client_id}
