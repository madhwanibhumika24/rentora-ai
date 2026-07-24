from datetime import date
from typing import List

from sqlalchemy.orm import Session

from app.models.due import Due, DueStatus
from app.models.user import User


def get_reminders_due_today(db: Session) -> List[dict]:
    today = date.today()
    dues = db.query(Due).filter(Due.status.in_([DueStatus.pending, DueStatus.overdue])).all()

    reminders = []
    for due in dues:
        days_until = (due.due_date - today).days
        stage = None
        if days_until == 5:
            stage = "5_days_before"
        elif days_until == 1:
            stage = "1_day_before"
        elif days_until == 0:
            stage = "due_today"
        elif days_until < 0:
            stage = "overdue"

        if stage:
            tenant = db.query(User).filter(User.id == due.tenant_id).first()
            reminders.append({
                "due_id": due.id,
                "tenant_id": due.tenant_id,
                "tenant_name": tenant.name if tenant else "Unknown",
                "tenant_phone": tenant.phone if tenant else None,
                "amount": float(due.amount),
                "late_fee": due.late_fee,
                "total_amount": due.total_amount,
                "due_date": due.due_date.isoformat(),
                "stage": stage,
                "days_until_due": days_until,
            })

    return reminders