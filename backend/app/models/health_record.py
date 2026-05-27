from sqlalchemy import Column, Integer, Float, String, Text, Date, DateTime, Boolean, ForeignKey, func
from app.core.database import Base


class HealthRecord(Base):
    __tablename__ = "health_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    record_date = Column(Date, nullable=False)
    weight_kg = Column(Float, nullable=True)
    calories_intake = Column(Integer, default=0)
    diet_compliance = Column(Float, default=0.0)
    mood = Column(String(50), default="")
    notes = Column(Text, default="")
    plan_followed = Column(Boolean, nullable=True, default=None)
    created_at = Column(DateTime, server_default=func.now())
