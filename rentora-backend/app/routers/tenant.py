from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import razorpay

from app.database import get_db
from app.config import settings
from app.core.deps import require_tenant
from app.core.payments import get_razorpay_client
from app.models.user import User
from app.models.property import Property
from app.models.room import Room
from app.models.booking import Booking, BookingStatus
from app.models.property_photo import PropertyPhoto
from app.models.property_rule import PropertyRule
from app.models.call_request import CallRequest
from app.schemas.tenant import BookingCreate, BookingOut, BookingOrderOut, BookingVerifyRequest
from app.schemas.call_request import CallRequestCreate
from app.services.ai import calculate_match_score

# The token amount a tenant pays up front to book a room - 10% of the
# room's monthly rent. Kept as one constant so both endpoints below (and
# anyone reading this later) agree on exactly how it's calculated.
TOKEN_PERCENT = 0.10

router = APIRouter(prefix="/tenant", tags=["tenant"])


@router.get("/explore")
def explore_rooms(
    city: Optional[str] = None,
    max_rent: Optional[float] = None,
    budget: Optional[float] = None,
    room_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Returns one card per PROPERTY (not per room) - a PG with 3 room types
    used to show up as 3 separate cards on the explore page, which was
    confusing since it's really just one place. Now every available room
    at a property gets folded into a single summary: the rent range, the
    room types on offer, and the best match score among its rooms.
    Clicking the card still goes to the property page, which lists every
    individual room.
    """
    query = db.query(Room).join(Property).filter(Room.is_available == True)
    if city:
        query = query.filter(Property.city.ilike(f"%{city}%"))
    if max_rent is not None:
        query = query.filter(Room.rent_amount <= max_rent)
    if room_type:
        query = query.filter(Room.room_type == room_type)
    rooms = query.all()

    # Group the matching rooms by their property id.
    grouped = {}
    for room in rooms:
        pid = room.property_id
        if pid not in grouped:
            grouped[pid] = {
                "property_id": pid,
                "property_name": room.property.name,
                "city": room.property.city,
                "room_types": set(),
                "rent_min": float(room.rent_amount),
                "rent_max": float(room.rent_amount),
                "total_available_beds": 0,
                "room_count": 0,
                "match_score": 0,
            }
        entry = grouped[pid]
        rent = float(room.rent_amount)
        score = calculate_match_score(room, city, budget)

        entry["room_types"].add(room.room_type.value if hasattr(room.room_type, "value") else room.room_type)
        entry["rent_min"] = min(entry["rent_min"], rent)
        entry["rent_max"] = max(entry["rent_max"], rent)
        entry["total_available_beds"] += room.bed_count
        entry["room_count"] += 1
        entry["match_score"] = max(entry["match_score"], score)

    results = []
    for entry in grouped.values():
        entry["room_types"] = sorted(entry["room_types"])
        results.append(entry)

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
        # Needed so the tenant's chat widget knows who to message.
        "owner_id": property_obj.owner_id,
        # Optional - only set if the owner told us this building has floors.
        "total_floors": property_obj.total_floors,
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
                "floor_number": r.floor_number,
                "room_number": r.room_number,
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


def get_bookable_room(db: Session, room_id: int, tenant_id: int) -> Room:
    """
    Shared check used by every booking-creation path below (the plain
    "dev mode" booking, and both steps of the real token-payment flow):
    the room has to still be available, and this tenant can't already
    have an active request/booking on it. Raises a 404/400 if either
    check fails, otherwise hands back the Room so the caller can use it.
    """
    room = db.query(Room).filter(Room.id == room_id, Room.is_available == True).first()
    if room is None:
        raise HTTPException(status_code=404, detail="Room not available")

    # A cancelled booking doesn't count, so a tenant can still try again
    # after cancelling (or after a previous stay there ended).
    already_booked = (
        db.query(Booking)
        .filter(
            Booking.tenant_id == tenant_id,
            Booking.room_id == room_id,
            Booking.status != BookingStatus.cancelled,
        )
        .first()
    )
    if already_booked is not None:
        raise HTTPException(status_code=400, detail="You already have a booking request for this room.")

    return room


@router.post("/bookings", response_model=BookingOut)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant),
):
    """
    The simple "no payment gateway configured" booking path - used as a
    fallback by the frontend when Razorpay keys aren't set up yet. Books
    the room directly with no token payment attached.
    """
    room = get_bookable_room(db, payload.room_id, current_user.id)

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


@router.post("/bookings/create-order", response_model=BookingOrderOut)
def create_booking_order(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant),
):
    """
    Step 1 of the real token-payment flow: check the room can actually be
    booked, work out the token amount (10% of rent), and ask Razorpay to
    create an "order" for it. The frontend uses this to open the Razorpay
    popup - no money moves yet, no Booking row is created yet either.
    """
    room = get_bookable_room(db, payload.room_id, current_user.id)

    client = get_razorpay_client()
    if client is None:
        raise HTTPException(
            status_code=400,
            detail="Payment gateway not configured. Use the dev-mode booking instead.",
        )

    token_amount = round(float(room.rent_amount) * TOKEN_PERCENT, 2)
    amount_in_paise = int(round(token_amount * 100))

    order = client.order.create({
        "amount": amount_in_paise,
        "currency": "INR",
        "receipt": f"booking_room_{room.id}",
    })

    return BookingOrderOut(
        order_id=order["id"],
        amount=amount_in_paise,
        currency="INR",
        key_id=settings.razorpay_key_id,
        room_id=room.id,
        token_amount=token_amount,
    )


@router.post("/bookings/verify-payment", response_model=BookingOut)
def verify_booking_payment(
    payload: BookingVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant),
):
    """
    Step 2 of the real token-payment flow: after the tenant pays inside
    the Razorpay popup, the frontend sends back the order/payment/
    signature values. We verify the signature ourselves (so a booking
    can't be faked by just calling this endpoint with made-up values),
    then finally create the Booking - re-checking the room is still
    bookable in case someone else grabbed it while the popup was open.
    """
    room = get_bookable_room(db, payload.room_id, current_user.id)

    client = get_razorpay_client()
    if client is None:
        raise HTTPException(status_code=400, detail="Payment gateway not configured")

    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": payload.razorpay_order_id,
            "razorpay_payment_id": payload.razorpay_payment_id,
            "razorpay_signature": payload.razorpay_signature,
        })
    except razorpay.errors.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Payment verification failed")

    token_amount = round(float(room.rent_amount) * TOKEN_PERCENT, 2)

    booking = Booking(
        tenant_id=current_user.id,
        room_id=room.id,
        status=BookingStatus.requested,
        move_in_date=payload.move_in_date,
        token_amount=token_amount,
        token_paid=True,
        razorpay_payment_id=payload.razorpay_payment_id,
    )
    db.add(booking)

    # Real money has now changed hands, so the room is reserved right
    # away instead of waiting for the owner to confirm - otherwise a
    # second tenant could pay a token for the same room before the owner
    # gets around to it. (The plain no-payment "dev mode" booking above
    # doesn't do this - it's just a request, nothing's been paid yet.)
    room.is_available = False

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
            "token_amount": float(b.token_amount) if b.token_amount is not None else None,
            "token_paid": b.token_paid,
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

    # If the room had been reserved for this booking, free it back up so
    # other tenants can book it again. That covers two cases now: the
    # owner already confirmed it, OR the tenant paid a token (which
    # reserves the room immediately, before the owner confirms anything).
    if booking.status == BookingStatus.confirmed or booking.token_paid:
        room = db.query(Room).filter(Room.id == booking.room_id).first()
        if room is not None:
            room.is_available = True

    booking.status = BookingStatus.cancelled
    db.commit()
    db.refresh(booking)
    return booking