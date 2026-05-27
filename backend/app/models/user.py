from sqlalchemy import Column, Integer, BigInteger, String, Float, Enum as SAEnum, DateTime, func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    openid = Column(String(64), unique=True, nullable=True, default=None)
    nickname = Column(String(100), default="")
    phone = Column(String(20), default="")
    gender = Column(String(10), default="unknown")
    age = Column(Integer, default=25)
    height_cm = Column(Float, default=170.0)
    weight_kg = Column(Float, default=70.0)
    body_fat_pct = Column(Float, default=20.0)
    goal_type = Column(String(20), default="healthy")
    target_weight_kg = Column(Float, default=70.0)
    cooking_level = Column(String(10), default="medium")
    is_admin = Column(Integer, default=0)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    address = Column(String(200), default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
