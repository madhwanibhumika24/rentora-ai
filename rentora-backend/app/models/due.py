import enum
from datetime import date
from sqlalchemy import Column, Integer, ForeignKey, Numeric, Enum, Date, String
from sqlalchemy.orm import relationship

from app.database import Base

LATE_FEE_PER_DAY = 50


class DueStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    overdue = "overdue"


class Due(Base):
    __tablename__ = "dues"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category = Column(String(50), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    due_date = Column(Date, nullable=False)
    status = Column(Enum(DueStatus), nullable=False, default=DueStatus.pending)

    payments = relationship("Payment", back_populates="due")

    @property
    def late_fee(self) -> float:
        if self.status == DueStatus.paid:
            return 0.0
        today = date.today()
        if today <= self.due_date:
            return 0.0
        days_overdue = (today - self.due_date).days
        return float(days_overdue * LATE_FEE_PER_DAY)

    @property
    def total_amount(self) -> float:
        return float(self.amount) + self.late_fee