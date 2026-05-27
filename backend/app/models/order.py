from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, func
from app.core.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    meal_plan_id = Column(Integer, ForeignKey("meal_plans.id", ondelete="CASCADE"), nullable=False)
    day_index = Column(Integer, nullable=False)
    delivery_date = Column(Date, nullable=False)
    status = Column(String(20), default="confirmed")
    items_json = Column(Text, default="[]")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
