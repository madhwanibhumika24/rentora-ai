import enum
from sqlalchemy import Column, Integer, ForeignKey, String, Text, Enum, DateTime
from sqlalchemy.sql import func

from app.database import Base


class ComplaintStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    category = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    photo_url = Column(String(255), nullable=True)
    status = Column(Enum(ComplaintStatus), nullable=False, default=ComplaintStatus.open)
    created_at = Column(DateTime(timezone=True), server_default=func.now())