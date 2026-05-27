from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, func
from app.core.database import Base


class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50), default="其他")
    calories_per_100g = Column(Integer, default=0)
    protein_per_100g = Column(Float, default=0.0)
    carbs_per_100g = Column(Float, default=0.0)
    fat_per_100g = Column(Float, default=0.0)
    estimated_price_per_500g = Column(Float, default=0.0)
    unit = Column(String(20), default="g")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
