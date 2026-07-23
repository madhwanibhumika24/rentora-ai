from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import require_tenant
from app.models.user import User
from app.models.property import Property
from app.models.room import Room
from app.models.booking import Booking, BookingStatus
from app.schemas.tenant import BookingCreate, BookingOut
from app.services.ai import calculate_match_score

router = APIRouter(prefix="/tenant", tags=["tenant"])


@router.get("/explore")
def explore_rooms(
    city: Optional[str] = None,
    max_rent: Optional[float] = None,
    budget: Optional[float] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Room).join(Property).filter(Room.is_available == True)
    if city:
        query = query.filter(Property.city.ilike(f"%{city}%"))
    if max_rent is not None:
        query = query.filter(Room.rent_amount <= max_rent)
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
    return {
        "id": property_obj.id,
        "name": property_obj.name,
        "city": property_obj.city,
        "address": property_obj.address,
        "amenities": property_obj.amenities,
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


@router.post("/bookings", response_model=BookingOut)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant),
):
    room = db.query(Room).filter(Room.id == payload.room_id, Room.is_available == True).first()
    if room is None:
        raise HTTPException(status_code=404, detail="Room not available")

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
    return db.query(Booking).filter(Booking.tenant_id == current_user.id).all()