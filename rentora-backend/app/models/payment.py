from sqlalchemy import Column, Integer, ForeignKey, Numeric, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    due_id = Column(Integer, ForeignKey("dues.id"), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    method = Column(String(30), nullable=False)
    transaction_id = Column(String(100), nullable=True)
    paid_at = Column(DateTime(timezone=True), server_default=func.now())

    due = relationship("Due", back_populates="payments")