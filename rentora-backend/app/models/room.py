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
    # Optional - only set if the owner's property actually has floors.
    # Left blank (NULL), a room just shows up without a floor label.
    floor_number = Column(Integer, nullable=True)
    # Optional label like "101" or "G-2" - a string (not a number) since
    # room numbers aren't always plain digits.
    room_number = Column(String(20), nullable=True)

    property = relationship("Property", back_populates="rooms")
    bookings = relationship("Booking", back_populates="room")