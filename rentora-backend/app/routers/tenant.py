from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import require_tenant
from app.models.user import User
from app.models.property import Property
from app.models.room import Room
from app.models.booking import Booking, BookingStatus
from app.models.property_photo import PropertyPhoto
from app.models.property_rule import PropertyRule
from app.models.call_request import CallRequest
from app.schemas.tenant import BookingCreate, BookingOut
from app.schemas.call_request import CallRequestCreate
from app.services.ai import calculate_match_score

router = APIRouter(prefix="/tenant", tags=["tenant"])


@router.get("/explore")
def explore_rooms(
    city: Optional[str] = None,
    max_rent: Optional[float] = None,
    budget: Optional[float] = None,
    room_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Room).join(Property).filter(Room.is_available == True)
    if city:
        query = query.filter(Property.city.ilike(f"%{city}%"))
    if max_rent is not None:
        query = query.filter(Room.rent_amount <= max_rent)
    if room_type:
        query = query.filter(Room.room_type == room_type)
    rooms = query.all()

    results = []
    for room in rooms:
        results.append({
            "id": room.id,
            "property_id": room.property_id,
            "property_name": room.property.name,
            "city": room.property.city,
            "room_type": room.room_type,
            "bed_count": room.bed_count,
            "rent_amount": float(room.rent_amount),
            "is_available": room.is_available,
            "match_score": calculate_match_score(room, city, budget),
        })

    results.sort(key=lambda r: r["match_score"], reverse=True)
    return results

@router.get("/properties/{property_id}")
def get_property_detail(property_id: int, db: Session = Depends(get_db)):
    property_obj = db.query(Property).filter(Property.id == property_id).first()
    if property_obj is None:
        raise HTTPException(status_code=404, detail="Property not found")
    rooms = db.query(Room).filter(Room.property_id == property_id).all()
    photos = db.query(PropertyPhoto).filter(PropertyPhoto.property_id == property_id).all()
    rules = db.query(PropertyRule).filter(PropertyRule.property_id == property_id).all()
    return {
        "id": property_obj.id,
        "name": property_obj.name,
        "city": property_obj.city,
        "address": property_obj.address,
        "amenities": property_obj.amenities,
        # Both of these are optional extras - they'll just be empty
        # lists if the owner hasn't added any yet.
        "photos": [p.image_url for p in photos],
        "rules": [r.text for r in rules],
        "rooms": [
            {
                "id": r.id,
                "room_type": r.room_type,
                "bed_count": r.bed_count,
                "rent_amount": float(r.rent_amount),
                "is_available": r.is_available,
            }
            for r in rooms
        ],
    }


@router.post("/properties/{property_id}/request-call")
def request_call(
    property_id: int,
    payload: CallRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant),
):
    property_obj = db.query(Property).filter(Property.id == property_id).first()
    if property_obj is None:
        raise HTTPException(status_code=404, detail="Property not found")

    call_request = CallRequest(
        tenant_id=current_user.id,
        property_id=property_id,
        # Use the phone number they typed in, or fall back to the one
        # saved on their account (if any).
        phone=payload.phone or current_user.phone,
        note=payload.note,
    )
    db.add(call_request)
    db.commit()
    return {"message": "Request sent! The owner will call you soon."}


@router.post("/bookings", response_model=BookingOut)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant),
):
    room = db.query(Room).filter(Room.id == payload.room_id, Room.is_available == True).first()
    if room is None:
        raise HTTPException(status_code=404, detail="Room not available")

    # Stop the tenant from sending the same booking request over and over.
    # A cancelled booking doesn't count, so they can still try again later.
    already_booked = (
        db.query(Booking)
        .filter(
            Booking.tenant_id == current_user.id,
            Booking.room_id == payload.room_id,
            Booking.status != BookingStatus.cancelled,
        )
        .first()
    )
    if already_booked is not None:
        raise HTTPException(status_code=400, detail="You already have a booking request for this room.")

    booking = Booking(
        tenant_id=current_user.id,
        room_id=room.id,
        status=BookingStatus.requested,
        move_in_date=payload.move_in_date,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/bookings", response_model=List[BookingOut])
def list_my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant),
):
    bookings = db.query(Booking).filter(Booking.tenant_id == current_user.id).all()
    results = []
    for b in bookings:
        results.append({
            "id": b.id,
            "tenant_id": b.tenant_id,
            "room_id": b.room_id,
            "status": b.status,
            "move_in_date": b.move_in_date,
            "created_at": b.created_at,
            "property_id": b.room.property_id,
            "property_name": b.room.property.name,
            "city": b.room.property.city,
            "room_type": b.room.room_type,
            "rent_amount": float(b.room.rent_amount),
        })
    return results


@router.patch("/bookings/{booking_id}/cancel", response_model=BookingOut)
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant),
):
    booking = (
        db.query(Booking)
        .filter(Booking.id == booking_id, Booking.tenant_id == current_user.id)
        .first()
    )
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status == BookingStatus.cancelled:
        raise HTTPException(status_code=400, detail="This booking is already cancelled")

    # If the room had been reserved for this booking, free it back up
    # so other tenants can book it again.
    if booking.status == BookingStatus.confirmed:
        room = db.query(Room).filter(Room.id == booking.room_id).first()
        if room is not None:
            room.is_available = True

    booking.status = BookingStatus.cancelled
    db.commit()
    db.refresh(booking)
    return booking