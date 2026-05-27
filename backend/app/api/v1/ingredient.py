from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.ingredient import Ingredient
from app.schemas import IngredientResponse

router = APIRouter(prefix="/api/v1/ingredient", tags=["食材库"])


@router.get("/list", response_model=list[IngredientResponse])
async def list_ingredients(category: str = Query(default=""), search: str = Query(default=""),
                           db: AsyncSession = Depends(get_db)):
    q = select(Ingredient).where(Ingredient.is_active == True)
    if category:
        q = q.where(Ingredient.category == category)
    if search:
        q = q.where(Ingredient.name.contains(search))
    q = q.order_by(Ingredient.category, Ingredient.name)
    result = await db.execute(q)
    return [IngredientResponse.model_validate(r) for r in result.scalars().all()]


@router.get("/categories")
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Ingredient.category).where(Ingredient.is_active == True).distinct()
    )
    return {"categories": sorted([r[0] for r in result.all()])}
