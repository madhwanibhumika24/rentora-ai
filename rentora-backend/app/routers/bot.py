from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import require_tenant
from app.models.user import User
from app.models.booking import Booking, BookingStatus
from app.models.room import Room
from app.schemas.bot import BotMessageRequest, BotMessageResponse

router = APIRouter(prefix="/bot", tags=["bot"])

MENU_OPTIONS = ["Raise a complaint", "More details about my PG", "I have a doubt", "Request a call"]


def _has_active_booking(db: Session, tenant_id: int) -> bool:
    return (
        db.query(Booking)
        .filter(Booking.tenant_id == tenant_id, Booking.status != BookingStatus.cancelled)
        .first()
        is not None
    )


@router.post("/message", response_model=BotMessageResponse)
def bot_message(
    payload: BotMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant),
):
    booked = _has_active_booking(db, current_user.id)

    if payload.intent == "menu":
        return BotMessageResponse(reply="Hi! How can I help you?", options=MENU_OPTIONS)

    if payload.intent == "raise_complaint":
        if not booked:
            return BotMessageResponse(
                reply="You haven't booked a PG yet. Book a room first to raise a complaint.",
                options=["Explore rooms"],
            )
        return BotMessageResponse(
            reply="Sure, what category is this about? Submit it via POST /tenant/complaints.",
            options=["Electrical", "Plumbing", "Wifi", "Food"],
        )

    if payload.intent == "pg_details":
        if not booked:
            return BotMessageResponse(
                reply="You haven't booked a PG yet - book one to see what's included in your rent.",
                options=[],
            )
        booking = (
            db.query(Booking)
            .filter(Booking.tenant_id == current_user.id, Booking.status != BookingStatus.cancelled)
            .first()
        )
        room = db.query(Room).filter(Room.id == booking.room_id).first()
        return BotMessageResponse(
            reply=f"Your rent of Rs {room.rent_amount} covers bed, wifi, and housekeeping. Electricity and food are billed separately.",
            options=[],
        )

    if payload.intent == "doubt":
        return BotMessageResponse(reply="Sure, ask away - type your question.", options=[])

    if payload.intent == "request_call":
        return BotMessageResponse(reply="Connecting you with the owner. Call requested.", options=[])

    return BotMessageResponse(reply="Sorry, I didn't understand that.", options=MENU_OPTIONS)