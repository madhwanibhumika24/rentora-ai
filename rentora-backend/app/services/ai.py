from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models.room import Room
from app.models.due import Due, DueStatus


def calculate_match_score(room: Room, city: Optional[str] = None, budget: Optional[float] = None) -> int:
    score = 70

    if city:
        room_city = room.property.city.lower()
        if room_city == city.lower():
            score += 15
        elif city.lower() in room_city:
            score += 8

    if budget:
        rent = float(room.rent_amount)
        if rent <= budget:
            closeness = 1 - (budget - rent) / budget if budget > 0 else 0
            score += int(15 * min(closeness, 1))
        else:
            over = (rent - budget) / budget
            score -= int(20 * min(over, 1))

    return max(50, min(score, 99))


def calculate_risk_score(db: Session, tenant_id: int) -> dict:
    dues = db.query(Due).filter(Due.tenant_id == tenant_id).all()
    if not dues:
        return {"risk_level": "low", "score": 0, "reason": "No payment history yet"}

    total = len(dues)
    overdue_count = 0
    late_paid_count = 0

    for due in dues:
        if due.status == DueStatus.overdue:
            overdue_count += 1
        elif due.status == DueStatus.pending and due.due_date < date.today():
            overdue_count += 1
        elif due.status == DueStatus.paid:
            for payment in due.payments:
                if payment.paid_at.date() > due.due_date:
                    late_paid_count += 1
                    break

    risk_points = (overdue_count * 2) + late_paid_count
    ratio = risk_points / total if total else 0

    if ratio >= 0.5:
        level = "high"
    elif ratio >= 0.2:
        level = "medium"
    else:
        level = "low"

    return {
        "risk_level": level,
        "score": round(ratio * 100),
        "total_dues": total,
        "overdue_count": overdue_count,
        "late_paid_count": late_paid_count,
    }