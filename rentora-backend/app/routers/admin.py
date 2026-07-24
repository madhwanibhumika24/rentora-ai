from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.reminders import get_reminders_due_today

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/reminders/due-today")
def reminders_due_today(db: Session = Depends(get_db)):
    return get_reminders_due_today(db)