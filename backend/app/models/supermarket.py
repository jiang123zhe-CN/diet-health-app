from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, func, UniqueConstraint
from app.core.database import Base


class Supermarket(Base):
    __tablename__ = "supermarkets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    address = Column(String(300), default="")
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    contact = Column(String(50), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class SupermarketAssignment(Base):
    __tablename__ = "supermarket_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    supermarket_id = Column(Integer, ForeignKey("supermarkets.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assigned_at = Column(DateTime, server_default=func.now())

    __table_args__ = (UniqueConstraint("supermarket_id", "user_id"),)
