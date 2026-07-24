from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import require_owner, require_tenant
from app.models.user import User
from app.models.due import Due, DueStatus
from app.models.payment import Payment
from app.schemas.due import DueCreate, DueOut, PaymentOut

router = APIRouter(tags=["dues"])


@router.post("/owner/dues", response_model=DueOut)
def create_due(
    payload: DueCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    due = Due(
        tenant_id=payload.tenant_id,
        category=payload.category,
        amount=payload.amount,
        due_date=payload.due_date,
        status=DueStatus.pending,
    )
    db.add(due)
    db.commit()
    db.refresh(due)
    return due


@router.get("/tenant/dues", response_model=List[DueOut])
def list_my_dues(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant),
):
    return db.query(Due).filter(Due.tenant_id == current_user.id).all()


@router.post("/tenant/dues/{due_id}/pay", response_model=PaymentOut)
def pay_due(
    due_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant),
):
    due = (
        db.query(Due)
        .filter(Due.id == due_id, Due.tenant_id == current_user.id)
        .first()
    )
    if due is None:
        raise HTTPException(status_code=404, detail="Due not found")
    if due.status == DueStatus.paid:
        raise HTTPException(status_code=400, detail="Due already paid")

    amount_to_charge = due.total_amount  # includes late fee if overdue

    payment = Payment(
        due_id=due.id,
        amount=amount_to_charge,
        method="upi",
        transaction_id=f"TXN{due.id:06d}",
    )
    due.status = DueStatus.paid
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


@router.get("/tenant/payments", response_model=List[PaymentOut])
def list_my_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant),
):
    return (
        db.query(Payment)
        .join(Due)
        .filter(Due.tenant_id == current_user.id)
        .all()
    )