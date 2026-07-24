from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models.room import Room
from app.models.property import Property
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


def suggest_price(db: Session, room: Room) -> dict:
    comparable_rents = (
        db.query(Room.rent_amount)
        .join(Property)
        .filter(
            Property.city == room.property.city,
            Room.room_type == room.room_type,
            Room.id != room.id,
        )
        .all()
    )
    rents = [float(r[0]) for r in comparable_rents]
    current_rent = float(room.rent_amount)

    if not rents:
        return {
            "current_rent": current_rent,
            "suggested_rent": current_rent,
            "comparable_count": 0,
            "message": "Not enough comparable listings in this city yet to suggest a price.",
        }

    avg_rent = sum(rents) / len(rents)
    suggested = round(avg_rent / 50) * 50

    if current_rent < avg_rent * 0.9:
        message = "Your rent is below market average - you could increase it."
    elif current_rent > avg_rent * 1.1:
        message = "Your rent is above market average - consider lowering it to stay competitive."
    else:
        message = "Your rent is well aligned with the market."

    return {
        "current_rent": current_rent,
        "market_average": round(avg_rent, 2),
        "suggested_rent": suggested,
        "comparable_count": len(rents),
        "message": message,
    }