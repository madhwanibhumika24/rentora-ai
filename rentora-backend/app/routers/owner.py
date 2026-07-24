from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import require_owner
from app.models.user import User
from app.models.property import Property
from app.models.room import Room
from app.models.booking import Booking, BookingStatus
from app.schemas.property import PropertyCreate, PropertyOut, RoomCreate, RoomOut
from app.schemas.tenant import BookingOut, BookingStatusUpdate
from app.services.ai import calculate_risk_score

router = APIRouter(prefix="/owner", tags=["owner"])


@router.post("/properties", response_model=PropertyOut)
def create_property(
    payload: PropertyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    property_obj = Property(
        owner_id=current_user.id,
        name=payload.name,
        city=payload.city,
        address=payload.address,
        amenities=payload.amenities,
    )
    db.add(property_obj)
    db.commit()
    db.refresh(property_obj)
    return property_obj


@router.get("/properties", response_model=List[PropertyOut])
def list_properties(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    return db.query(Property).filter(Property.owner_id == current_user.id).all()


@router.post("/properties/{property_id}/rooms", response_model=RoomOut)
def add_room(
    property_id: int,
    payload: RoomCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    property_obj = (
        db.query(Property)
        .filter(Property.id == property_id, Property.owner_id == current_user.id)
        .first()
    )
    if property_obj is None:
        raise HTTPException(status_code=404, detail="Property not found")

    room = Room(
        property_id=property_obj.id,
        room_type=payload.room_type,
        bed_count=payload.bed_count,
        rent_amount=payload.rent_amount,
    )
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


@router.get("/properties/{property_id}/rooms", response_model=List[RoomOut])
def list_rooms(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    property_obj = (
        db.query(Property)
        .filter(Property.id == property_id, Property.owner_id == current_user.id)
        .first()
    )
    if property_obj is None:
        raise HTTPException(status_code=404, detail="Property not found")

    return db.query(Room).filter(Room.property_id == property_id).all()


@router.get("/bookings", response_model=List[BookingOut])
def list_booking_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    return (
        db.query(Booking)
        .join(Room)
        .join(Property)
        .filter(Property.owner_id == current_user.id)
        .all()
    )


@router.patch("/bookings/{booking_id}", response_model=BookingOut)
def update_booking_status(
    booking_id: int,
    payload: BookingStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    booking = (
        db.query(Booking)
        .join(Room)
        .join(Property)
        .filter(Booking.id == booking_id, Property.owner_id == current_user.id)
        .first()
    )
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")

    booking.status = payload.status
    if payload.status == BookingStatus.confirmed:
        room = db.query(Room).filter(Room.id == booking.room_id).first()
        room.is_available = False

    db.commit()
    db.refresh(booking)
    return booking


@router.get("/tenants/{tenant_id}/risk-score")
def get_tenant_risk_score(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    has_relation = (
        db.query(Booking)
        .join(Room)
        .join(Property)
        .filter(Booking.tenant_id == tenant_id, Property.owner_id == current_user.id)
        .first()
    )
    if has_relation is None:
        raise HTTPException(status_code=404, detail="Tenant not found under your properties")

    return calculate_risk_score(db, tenant_id)