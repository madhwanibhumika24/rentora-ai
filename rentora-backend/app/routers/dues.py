from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import razorpay

from app.database import get_db
from app.config import settings
from app.core.deps import require_owner, require_tenant
from app.core.payments import get_razorpay_client
from app.models.user import User
from app.models.due import Due, DueStatus
from app.models.payment import Payment
from app.models.booking import Booking, BookingStatus
from app.models.room import Room
from app.models.property import Property
from app.schemas.due import DueCreate, DueOut, PaymentOut, OrderOut, VerifyPaymentRequest

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


@router.get("/owner/dues")
def list_dues_for_my_tenants(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    """
    Shows the owner every due they've raised for tenants living in their
    properties, along with whether it's been paid yet. We attach the
    tenant's name here since the frontend can't look that up itself.
    """
    tenant_ids = [
        row[0]
        for row in (
            db.query(Booking.tenant_id)
            .join(Room)
            .join(Property)
            .filter(Property.owner_id == current_user.id, Booking.status == BookingStatus.confirmed)
            .distinct()
            .all()
        )
    ]

    dues = (
        db.query(Due)
        .filter(Due.tenant_id.in_(tenant_ids))
        .order_by(Due.due_date.desc())
        .all()
    )

    # Look up all the tenant names in one go instead of one query per due.
    tenants = db.query(User).filter(User.id.in_(tenant_ids)).all()
    tenant_names = {t.id: t.name for t in tenants}

    results = []
    for d in dues:
        results.append({
            "id": d.id,
            "tenant_id": d.tenant_id,
            "tenant_name": tenant_names.get(d.tenant_id, "Unknown"),
            "category": d.category,
            "amount": float(d.amount),
            "due_date": d.due_date,
            "status": d.status,
            "late_fee": d.late_fee,
            "total_amount": d.total_amount,
        })
    return results


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


@router.post("/tenant/dues/{due_id}/create-order", response_model=OrderOut)
def create_payment_order(
    due_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant),
):
    """
    Step 1 of a real payment: ask Razorpay to create an "order" for this
    due. The frontend uses the order details to open the Razorpay popup.
    No money moves yet - that happens when the tenant pays inside the popup.
    """
    due = (
        db.query(Due)
        .filter(Due.id == due_id, Due.tenant_id == current_user.id)
        .first()
    )
    if due is None:
        raise HTTPException(status_code=404, detail="Due not found")
    if due.status == DueStatus.paid:
        raise HTTPException(status_code=400, detail="Due already paid")

    client = get_razorpay_client()
    if client is None:
        raise HTTPException(
            status_code=400,
            detail="Payment gateway not configured. Use the dev-mode pay button instead.",
        )

    # Razorpay wants the amount in paise (1 rupee = 100 paise), not rupees.
    amount_in_paise = int(due.total_amount * 100)

    order = client.order.create({
        "amount": amount_in_paise,
        "currency": "INR",
        "receipt": f"due_{due.id}",
    })

    return OrderOut(
        order_id=order["id"],
        amount=amount_in_paise,
        currency="INR",
        key_id=settings.razorpay_key_id,
        due_id=due.id,
    )


@router.post("/tenant/dues/{due_id}/verify-payment", response_model=PaymentOut)
def verify_payment(
    due_id: int,
    payload: VerifyPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant),
):
    """
    Step 2 of a real payment: after the tenant pays inside the Razorpay
    popup, the frontend sends us back the order/payment/signature values.
    We check the signature ourselves so we know the payment is genuine
    and wasn't just made up by someone calling this endpoint directly.
    """
    due = (
        db.query(Due)
        .filter(Due.id == due_id, Due.tenant_id == current_user.id)
        .first()
    )
    if due is None:
        raise HTTPException(status_code=404, detail="Due not found")
    if due.status == DueStatus.paid:
        raise HTTPException(status_code=400, detail="Due already paid")

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

    payment = Payment(
        due_id=due.id,
        amount=due.total_amount,
        method="razorpay",
        transaction_id=payload.razorpay_payment_id,
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


@router.get("/tenant/transactions")
def list_my_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant),
):
    """
    Powers the "Transactions" section on the tenant dashboard. Money the
    tenant has actually paid comes from two different tables that don't
    know about each other - rent/due payments (Payment, tied to a Due)
    and booking deposits (a paid Booking) - so this combines both into
    one flat list, newest first, in a shape the frontend can render
    the same way no matter which kind a row is.
    """
    results = []

    due_payments = (
        db.query(Payment)
        .join(Due)
        .filter(Due.tenant_id == current_user.id)
        .all()
    )
    for p in due_payments:
        results.append({
            "id": "due-" + str(p.id),
            "type": "due",
            "label": p.due.category.capitalize() + " due",
            "amount": float(p.amount),
            "date": p.paid_at,
            "method": p.method,
            "transaction_id": p.transaction_id,
        })

    deposit_bookings = (
        db.query(Booking)
        .filter(Booking.tenant_id == current_user.id, Booking.token_paid == True)
        .all()
    )
    for b in deposit_bookings:
        results.append({
            "id": "booking-" + str(b.id),
            "type": "deposit",
            "label": "Booking deposit - " + b.room.property.name,
            "amount": float(b.token_amount) if b.token_amount is not None else 0,
            "date": b.created_at,
            "method": "razorpay",
            "transaction_id": b.razorpay_payment_id,
        })

    results.sort(key=lambda r: r["date"], reverse=True)
    return results