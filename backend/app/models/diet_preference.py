from sqlalchemy import Column, Integer, BigInteger, String, ForeignKey, PrimaryKeyConstraint
from app.core.database import Base


class UserDietPreference(Base):
    __tablename__ = "user_diet_preferences"
    __table_args__ = (PrimaryKeyConstraint("user_id", "preference_type", "item_name"),)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    preference_type = Column(String(20), nullable=False)
    item_name = Column(String(100), nullable=False)
