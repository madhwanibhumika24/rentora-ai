import enum
from sqlalchemy import Column, Integer, String, Enum, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class UserRole(str, enum.Enum):
    owner = "owner"
    tenant = "tenant"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    phone = Column(String(15), unique=True, nullable=True, index=True)
    is_email_verified = Column(Boolean, nullable=False, default=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.tenant)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    properties = relationship("Property", back_populates="owner")
    bookings = relationship("Booking", back_populates="tenant")