from sqlalchemy import Column, Integer, BigInteger, String, Float, Boolean, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class MealPlan(Base):
    __tablename__ = "meal_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_type = Column(String(10), default="7day")
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    status = Column(String(20), default="active")
    ai_generated = Column(Boolean, default=True)
    calories_target = Column(Integer, default=2000)
    protein_target_g = Column(Float, default=100.0)
    carbs_target_g = Column(Float, default=250.0)
    fat_target_g = Column(Float, default=65.0)
    created_at = Column(DateTime, server_default=func.now())

    meals = relationship("DailyMeal", back_populates="meal_plan", cascade="all, delete-orphan",
                         order_by="DailyMeal.day_index, DailyMeal.meal_type")


class DailyMeal(Base):
    __tablename__ = "daily_meals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meal_plan_id = Column(Integer, ForeignKey("meal_plans.id", ondelete="CASCADE"), nullable=False)
    day_index = Column(Integer, nullable=False)
    meal_type = Column(String(10), nullable=False)
    meal_source = Column(String(20), default="cook")
    meal_name = Column(String(200), default="")
    calories = Column(Integer, default=0)
    protein_g = Column(Float, default=0.0)
    carbs_g = Column(Float, default=0.0)
    fat_g = Column(Float, default=0.0)
    cooking_time_min = Column(Integer, default=15)
    instructions = Column(String(500), default="")
    is_user_modified = Column(Boolean, default=False)
    is_user_swapped = Column(Boolean, default=False)
    warning_shown = Column(Boolean, default=False)

    meal_plan = relationship("MealPlan", back_populates="meals")
    ingredients = relationship("MealIngredient", back_populates="meal", cascade="all, delete-orphan")


class MealIngredient(Base):
    __tablename__ = "meal_ingredients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meal_id = Column(Integer, ForeignKey("daily_meals.id", ondelete="CASCADE"), nullable=False)
    ingredient_name = Column(String(100), default="")
    quantity_g = Column(Float, default=100.0)

    meal = relationship("DailyMeal", back_populates="ingredients")
