from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    city = Column(String(80), nullable=False, index=True)
    address = Column(String(255), nullable=False)
    amenities = Column(String(255), nullable=True)
    # Optional - only filled in if the building actually has multiple
    # floors. NULL just means "not set", not "zero floors".
    total_floors = Column(Integer, nullable=True)
    # Optional too - a rough total the owner can give up front. It doesn't
    # have to match the number of rooms actually added below (those are
    # added one by one with their own type/rent/floor).
    total_rooms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="properties")
    rooms = relationship("Room", back_populates="property")