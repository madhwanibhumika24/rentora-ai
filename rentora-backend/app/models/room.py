import enum
from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, Enum, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


class RoomType(str, enum.Enum):
    single = "single"
    double = "double"
    triple = "triple"
    dorm = "dorm"


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    room_type = Column(Enum(RoomType), nullable=False, default=RoomType.double)
    bed_count = Column(Integer, nullable=False, default=1)
    rent_amount = Column(Numeric(10, 2), nullable=False)
    is_available = Column(Boolean, default=True)

    property = relationship("Property", back_populates="rooms")
    bookings = relationship("Booking", back_populates="room")