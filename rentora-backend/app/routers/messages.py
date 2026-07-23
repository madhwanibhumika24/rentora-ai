from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.message import Message
from app.schemas.message import MessageCreate, MessageOut

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("", response_model=MessageOut)
def send_message(
    payload: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    message = Message(
        sender_id=current_user.id,
        receiver_id=payload.receiver_id,
        property_id=payload.property_id,
        text=payload.text,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@router.get("/with/{other_user_id}", response_model=List[MessageOut])
def get_conversation(
    other_user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Message)
        .filter(
            or_(
                and_(Message.sender_id == current_user.id, Message.receiver_id == other_user_id),
                and_(Message.sender_id == other_user_id, Message.receiver_id == current_user.id),
            )
        )
        .order_by(Message.sent_at)
        .all()
    )