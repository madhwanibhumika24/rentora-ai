from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import require_owner, require_tenant
from app.models.user import User
from app.models.property import Property
from app.models.complaint import Complaint
from app.schemas.complaint import ComplaintCreate, ComplaintOut, ComplaintStatusUpdate

router = APIRouter(tags=["complaints"])


@router.post("/tenant/complaints", response_model=ComplaintOut)
def raise_complaint(
    payload: ComplaintCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant),
):
    complaint = Complaint(
        tenant_id=current_user.id,
        property_id=payload.property_id,
        category=payload.category,
        description=payload.description,
        photo_url=payload.photo_url,
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    return complaint


@router.get("/tenant/complaints", response_model=List[ComplaintOut])
def list_my_complaints(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant),
):
    return db.query(Complaint).filter(Complaint.tenant_id == current_user.id).all()


@router.get("/owner/complaints", response_model=List[ComplaintOut])
def list_property_complaints(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    return (
        db.query(Complaint)
        .join(Property)
        .filter(Property.owner_id == current_user.id)
        .all()
    )


@router.patch("/owner/complaints/{complaint_id}", response_model=ComplaintOut)
def update_complaint_status(
    complaint_id: int,
    payload: ComplaintStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    complaint = (
        db.query(Complaint)
        .join(Property)
        .filter(Complaint.id == complaint_id, Property.owner_id == current_user.id)
        .first()
    )
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")

    complaint.status = payload.status
    db.commit()
    db.refresh(complaint)
    return complaint