import enum
from sqlalchemy import Column, Integer, ForeignKey, Enum, Date, DateTime, Numeric, Boolean, String
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class BookingStatus(str, enum.Enum):
    requested = "requested"
    confirmed = "confirmed"
    cancelled = "cancelled"


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False, index=True)
    status = Column(Enum(BookingStatus), nullable=False, default=BookingStatus.requested)
    move_in_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Deposit payment - one month's rent, paid at booking time to secure
    # the room. Nullable/false by default so bookings made before this
    # feature (or through the no-gateway dev fallback) still work fine
    # without one. (DB columns keep the "token_*" name from an earlier
    # version of this feature, back when it was a smaller booking fee.)
    token_amount = Column(Numeric(10, 2), nullable=True)
    token_paid = Column(Boolean, nullable=False, default=False)
    razorpay_payment_id = Column(String(100), nullable=True)

    tenant = relationship("User", back_populates="bookings")
    room = relationship("Room", back_populates="bookings")