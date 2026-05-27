from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, func
from app.core.database import Base


class DeliveryTask(Base):
    __tablename__ = "delivery_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    supermarket_id = Column(Integer, ForeignKey("supermarkets.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    meal_plan_id = Column(Integer, ForeignKey("meal_plans.id", ondelete="CASCADE"), nullable=False)
    day_index = Column(Integer, nullable=False)
    delivery_date = Column(Date, nullable=False)
    status = Column(String(20), default="pending")
    ingredients_json = Column(Text, default="[]")
    notes = Column(String(300), default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
