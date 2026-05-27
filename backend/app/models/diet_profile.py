from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func, JSON
from app.core.database import Base


class UserDietProfile(Base):
    __tablename__ = "user_diet_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    questionnaire_data = Column(JSON, default=dict)
    ai_profile_summary = Column(Text, default="")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
