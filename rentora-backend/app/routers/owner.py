import os
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import require_owner
from app.models.user import User
from app.models.property import Property
from app.models.room import Room
from app.models.booking import Booking, BookingStatus
from app.models.property_photo import PropertyPhoto
from app.models.property_rule import PropertyRule
from app.models.call_request import CallRequest
from app.models.complaint import Complaint
from app.models.community_post import CommunityPost
from app.models.message import Message
from app.schemas.property import (
    PropertyCreate,
    PropertyOut,
    PropertyUpdate,
    RoomCreate,
    RoomOut,
    PhotoOut,
    RuleCreate,
    RuleOut,
)
from app.schemas.tenant import BookingOut, BookingStatusUpdate
from app.services.ai import calculate_risk_score, suggest_price

router = APIRouter(prefix="/owner", tags=["owner"])

# Where uploaded property photos get saved on disk.
UPLOAD_DIR = "uploads/properties"


def get_owned_property(db: Session, property_id: int, owner_id: int) -> Property:
    """
    Small helper used by every photo/rule/feature endpoint below: look up
    a property and make sure it actually belongs to the logged-in owner.
    Raises a 404 if not, so a caller can never touch someone else's data.
    """
    property_obj = (
        db.query(Property)
        .filter(Property.id == property_id, Property.owner_id == owner_id)
        .first()
    )
    if property_obj is None:
        raise HTTPException(status_code=404, detail="Property not found")
    return property_obj


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
        total_floors=payload.total_floors,
        total_rooms=payload.total_rooms,
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


@router.delete("/properties/{property_id}")
def delete_property(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    """
    Deletes a property and everything that belongs to it - rooms (and any
    bookings on those rooms), photos (including the actual files on disk),
    rules, call requests, complaints, and community posts. This can't be
    undone, so the frontend always asks "are you sure?" before calling
    this - never wire this up to a button that fires without confirming.
    """
    property_obj = get_owned_property(db, property_id, current_user.id)

    # Bookings point at a room, not the property directly, so grab every
    # room's id first and delete their bookings before the rooms themselves.
    room_ids = [r.id for r in db.query(Room).filter(Room.property_id == property_id).all()]
    if room_ids:
        db.query(Booking).filter(Booking.room_id.in_(room_ids)).delete(synchronize_session=False)
        db.query(Room).filter(Room.property_id == property_id).delete(synchronize_session=False)

    # Delete photo files off disk too, not just their database rows.
    photos = db.query(PropertyPhoto).filter(PropertyPhoto.property_id == property_id).all()
    for photo in photos:
        file_path = photo.image_url.lstrip("/")
        if os.path.exists(file_path):
            os.remove(file_path)
    db.query(PropertyPhoto).filter(PropertyPhoto.property_id == property_id).delete(synchronize_session=False)

    db.query(PropertyRule).filter(PropertyRule.property_id == property_id).delete(synchronize_session=False)
    db.query(CallRequest).filter(CallRequest.property_id == property_id).delete(synchronize_session=False)
    db.query(Complaint).filter(Complaint.property_id == property_id).delete(synchronize_session=False)
    db.query(CommunityPost).filter(CommunityPost.property_id == property_id).delete(synchronize_session=False)
    # Messages can exist without a property attached, so just detach them
    # instead of deleting someone's chat history.
    db.query(Message).filter(Message.property_id == property_id).update(
        {"property_id": None}, synchronize_session=False
    )

    db.delete(property_obj)
    db.commit()
    return {"message": "Property deleted"}


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
        floor_number=payload.floor_number,
        room_number=payload.room_number,
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


# ----- Editing a property's details -----
# Covers everything from fixing a typo'd city/name/address to updating
# features (amenities) and the floor/room totals after creation - not
# everyone gets everything right (or filled in) on day one.

@router.patch("/properties/{property_id}", response_model=PropertyOut)
def update_property_features(
    property_id: int,
    payload: PropertyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    property_obj = get_owned_property(db, property_id, current_user.id)

    # Only touch a field if it was actually sent - this lets the same
    # endpoint be used for small one-off edits (like fixing a typo in the
    # city) without having to resend everything else.
    if payload.name is not None:
        property_obj.name = payload.name
    if payload.city is not None:
        property_obj.city = payload.city
    if payload.address is not None:
        property_obj.address = payload.address
    if payload.amenities is not None:
        property_obj.amenities = payload.amenities
    if payload.total_floors is not None:
        property_obj.total_floors = payload.total_floors
    if payload.total_rooms is not None:
        property_obj.total_rooms = payload.total_rooms

    db.commit()
    db.refresh(property_obj)
    return property_obj


# ----- Photos -----
# Entirely optional - an owner can add zero, one, or many photos.

@router.post("/properties/{property_id}/photos", response_model=PhotoOut)
def upload_property_photo(
    property_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    get_owned_property(db, property_id, current_user.id)

    folder = os.path.join(UPLOAD_DIR, str(property_id))
    os.makedirs(folder, exist_ok=True)

    # Give the file a random name so two uploads never overwrite each other.
    file_extension = os.path.splitext(file.filename)[1] or ".jpg"
    saved_filename = uuid.uuid4().hex + file_extension
    saved_path = os.path.join(folder, saved_filename)

    with open(saved_path, "wb") as saved_file:
        saved_file.write(file.file.read())

    photo = PropertyPhoto(
        property_id=property_id,
        image_url=f"/uploads/properties/{property_id}/{saved_filename}",
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


@router.get("/properties/{property_id}/photos", response_model=List[PhotoOut])
def list_property_photos(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    get_owned_property(db, property_id, current_user.id)
    return db.query(PropertyPhoto).filter(PropertyPhoto.property_id == property_id).all()


@router.delete("/properties/{property_id}/photos/{photo_id}")
def delete_property_photo(
    property_id: int,
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    get_owned_property(db, property_id, current_user.id)

    photo = (
        db.query(PropertyPhoto)
        .filter(PropertyPhoto.id == photo_id, PropertyPhoto.property_id == property_id)
        .first()
    )
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")

    # image_url looks like "/uploads/properties/3/abc.jpg" - drop the
    # leading slash so it matches a real path on disk, then delete it.
    file_path = photo.image_url.lstrip("/")
    if os.path.exists(file_path):
        os.remove(file_path)

    db.delete(photo)
    db.commit()
    return {"message": "Photo deleted"}


# ----- House rules -----
# Also optional. Stored one rule per row so they render as a clean list.

@router.post("/properties/{property_id}/rules", response_model=RuleOut)
def add_property_rule(
    property_id: int,
    payload: RuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    get_owned_property(db, property_id, current_user.id)

    rule = PropertyRule(property_id=property_id, text=payload.text)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/properties/{property_id}/rules", response_model=List[RuleOut])
def list_property_rules(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    get_owned_property(db, property_id, current_user.id)
    return db.query(PropertyRule).filter(PropertyRule.property_id == property_id).all()


@router.delete("/properties/{property_id}/rules/{rule_id}")
def delete_property_rule(
    property_id: int,
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    get_owned_property(db, property_id, current_user.id)

    rule = (
        db.query(PropertyRule)
        .filter(PropertyRule.id == rule_id, PropertyRule.property_id == property_id)
        .first()
    )
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")

    db.delete(rule)
    db.commit()
    return {"message": "Rule deleted"}


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


@router.get("/tenants")
def list_my_tenants(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    """
    Returns everyone with a CONFIRMED booking in one of this owner's
    properties. The owner picks a tenant from this list when raising a
    rent due, so we also send the room's rent as a suggested amount.
    """
    bookings = (
        db.query(Booking)
        .join(Room)
        .join(Property)
        .filter(Property.owner_id == current_user.id, Booking.status == BookingStatus.confirmed)
        .all()
    )

    results = []
    for b in bookings:
        results.append({
            "tenant_id": b.tenant_id,
            "tenant_name": b.tenant.name,
            "tenant_email": b.tenant.email,
            "property_name": b.room.property.name,
            "room_type": b.room.room_type,
            "rent_amount": float(b.room.rent_amount),
        })
    return results


@router.get("/call-requests")
def list_call_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    """
    Shows every "request a call" a tenant has sent for one of this
    owner's properties, newest first, with the tenant's name and phone
    attached so the owner knows who to call.
    """
    rows = (
        db.query(CallRequest, Property.name.label("property_name"), User.name.label("tenant_name"))
        .join(Property, CallRequest.property_id == Property.id)
        .join(User, CallRequest.tenant_id == User.id)
        .filter(Property.owner_id == current_user.id)
        .order_by(CallRequest.created_at.desc())
        .all()
    )

    results = []
    for call_request, property_name, tenant_name in rows:
        results.append({
            "id": call_request.id,
            "tenant_name": tenant_name,
            "phone": call_request.phone,
            "property_name": property_name,
            "note": call_request.note,
            "created_at": call_request.created_at,
        })
    return results


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


@router.get("/rooms/{room_id}/price-suggestion")
def get_price_suggestion(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    room = (
        db.query(Room)
        .join(Property)
        .filter(Room.id == room_id, Property.owner_id == current_user.id)
        .first()
    )
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")

    return suggest_price(db, room)