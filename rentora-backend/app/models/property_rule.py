from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func

from app.database import Base


class PropertyRule(Base):
    """One house rule for a property (e.g. "No smoking"). A property can have many."""

    __tablename__ = "property_rules"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    text = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
