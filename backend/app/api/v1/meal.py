import json
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.diet_preference import UserDietPreference
from app.models.diet_profile import UserDietProfile
from app.models.meal_plan import MealPlan, DailyMeal, MealIngredient
from app.models.ingredient import Ingredient
from app.models.order import Order
from app.schemas import (
    MealGenerateRequest, MealPlanResponse, MealPlanSummary, DailyMealResponse,
    IngredientItem, SwapRequest, SwapResponse, SwapWarningRequest,
    DishIngredientItem, DailyMealShoppingItem, DayShoppingGroup, DailyShoppingListResponse,
    OrderConfirmRequest, OrderResponse,
)
from app.services.ai_service import (
    build_meal_plan_system_prompt, build_swap_prompt, call_deepseek,
    extract_json, parse_meal_plan_response,
)
from app.services.nutrition import calc_tdee, calc_macros

router = APIRouter(prefix="/api/v1/meal", tags=["饮食方案"])


async def _get_user_prefs(user_id: int, db: AsyncSession) -> tuple[list, list, list]:
    result = await db.execute(
        select(UserDietPreference).where(UserDietPreference.user_id == user_id)
    )
    prefs = result.scalars().all()
    likes = [p.item_name for p in prefs if p.preference_type == "like"]
    dislikes = [p.item_name for p in prefs if p.preference_type == "dislike"]
    allergies = [p.item_name for p in prefs if p.preference_type == "allergy"]
    return likes, dislikes, allergies


@router.post("/generate", response_model=MealPlanResponse)
async def generate_meal_plan(req: MealGenerateRequest, user: User = Depends(get_current_user),
                             db: AsyncSession = Depends(get_db)):
    macros = calc_macros(calc_tdee(user.weight_kg, user.height_cm, user.age, user.gender),
                         user.weight_kg, user.goal_type)
    likes, dislikes, allergies = await _get_user_prefs(user.id, db)

    # Load dietary profile from questionnaire analysis
    diet_profile_summary = ""
    profile_result = await db.execute(
        select(UserDietProfile).where(UserDietProfile.user_id == user.id)
    )
    user_profile = profile_result.scalar_one_or_none()
    if user_profile and user_profile.ai_profile_summary:
        diet_profile_summary = user_profile.ai_profile_summary

    # Merge questionnaire restrictions with tag-based preferences
    if user_profile and user_profile.questionnaire_data:
        qdata = user_profile.questionnaire_data or {}
        for allergy in qdata.get("food_allergies", []):
            name = allergy.get("food", allergy.get("name", ""))
            if name and name not in allergies:
                allergies.append(name)
        for restriction in qdata.get("dietary_restrictions", []):
            if restriction and restriction not in dislikes:
                dislikes.append(restriction)

    # Load available ingredients from database
    ing_result = await db.execute(
        select(Ingredient.name).where(Ingredient.is_active == True).order_by(Ingredient.name)
    )
    available_ingredients = [r[0] for r in ing_result.all()]

    system_prompt = build_meal_plan_system_prompt(
        macros, user.cooking_level, likes, dislikes, allergies,
        diet_profile_summary=diet_profile_summary,
        available_ingredients=available_ingredients,
    )
    user_prompt = f"请生成{req.plan_type}天饮食方案"
    max_tokens = {"3day": 8000, "7day": 16000, "30day": 32000}.get(req.plan_type, 16000)

    raw = await call_deepseek(system_prompt, user_prompt, max_tokens=max_tokens)
    meals_data = parse_meal_plan_response(raw, macros)

    start_date = req.start_date or date.today()
    days = int(req.plan_type.replace("day", ""))
    plan = MealPlan(
        user_id=user.id, plan_type=req.plan_type,
        start_date=start_date, end_date=start_date + timedelta(days=days - 1),
        calories_target=macros["calories"], protein_target_g=macros["protein_g"],
        carbs_target_g=macros["carbs_g"], fat_target_g=macros["fat_g"],
    )
    db.add(plan)
    await db.flush()

    for m in meals_data:
        meal = DailyMeal(
            meal_plan_id=plan.id, day_index=m.get("day_index", m.get("day", 1)),
            meal_type=m.get("meal_type", "lunch"),
            meal_source=m.get("meal_source", "cook"),
            meal_name=m.get("meal_name", ""),
            calories=m.get("calories", 0),
            protein_g=m.get("protein_g", 0), carbs_g=m.get("carbs_g", 0),
            fat_g=m.get("fat_g", 0),
            cooking_time_min=m.get("cooking_time_min", 15),
            instructions=m.get("instructions", ""),
        )
        db.add(meal)
        await db.flush()
        for ing in m.get("ingredients", []):
            db.add(MealIngredient(meal_id=meal.id, ingredient_name=ing["name"],
                                   quantity_g=ing.get("quantity_g", 100)))

    await db.commit()
    await db.refresh(plan)
    return await _build_plan_response(plan, db)


@router.get("/plans", response_model=list[MealPlanSummary])
async def list_plans(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MealPlan)
        .options(selectinload(MealPlan.meals))
        .where(MealPlan.user_id == user.id)
        .order_by(MealPlan.created_at.desc()).limit(20)
    )
    plans = result.scalars().all()
    summaries = []
    for p in plans:
        meal_count = len(p.meals) if p.meals else 0
        summaries.append(MealPlanSummary(
            id=p.id, plan_type=p.plan_type, start_date=p.start_date, end_date=p.end_date,
            status=p.status, calories_target=p.calories_target, created_at=p.created_at,
            meal_count=meal_count,
        ))
    return summaries


@router.get("/plan/{plan_id}", response_model=MealPlanResponse)
async def get_plan(plan_id: int, user: User = Depends(get_current_user),
                   db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MealPlan)
        .options(selectinload(MealPlan.meals).selectinload(DailyMeal.ingredients))
        .where(MealPlan.id == plan_id, MealPlan.user_id == user.id)
    )
    plan = result.scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="方案不存在")
    return await _build_plan_response(plan, db)


@router.post("/swap", response_model=SwapResponse)
async def swap_ingredient(req: SwapRequest, user: User = Depends(get_current_user),
                          db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DailyMeal).where(DailyMeal.id == req.meal_id)
    )
    meal = result.scalar_one_or_none()
    if meal is None:
        raise HTTPException(status_code=404, detail="餐食不存在")

    meal_context = {
        "meal_name": meal.meal_name,
        "calories": meal.calories,
        "protein_g": meal.protein_g,
    }
    prompt = build_swap_prompt(req.current_ingredient, meal_context)
    raw = await call_deepseek(prompt, "请给出替换建议", max_tokens=2000)
    data = extract_json(raw)
    return SwapResponse(original=req.current_ingredient, alternatives=data.get("alternatives", []))


@router.post("/swap-warning")
async def confirm_swap_warning(req: SwapWarningRequest, user: User = Depends(get_current_user),
                               db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DailyMeal).where(DailyMeal.id == req.meal_id))
    meal = result.scalar_one_or_none()
    if meal is None:
        raise HTTPException(status_code=404, detail="餐食不存在")
    meal.is_user_swapped = True
    meal.warning_shown = True
    await db.commit()
    return {
        "message": "已确认替换",
        "warning": "替换后营养结构可能发生变化，本方案仅供参考，不构成医疗建议。",
        "meal_id": req.meal_id,
    }


async def _build_price_lookup(db: AsyncSession) -> dict[str, float]:
    result = await db.execute(select(Ingredient).where(Ingredient.is_active == True))
    return {ing.name: ing.estimated_price_per_500g for ing in result.scalars().all()}


@router.get("/ingredients/{plan_id}")
async def get_shopping_list(plan_id: int, period: str = "7day", group_by: str = "flat",
                            user: User = Depends(get_current_user),
                            db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MealPlan).where(MealPlan.id == plan_id, MealPlan.user_id == user.id)
    )
    plan = result.scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="方案不存在")

    meals_result = await db.execute(
        select(DailyMeal).options(selectinload(DailyMeal.ingredients))
        .where(DailyMeal.meal_plan_id == plan_id)
        .order_by(DailyMeal.day_index, DailyMeal.meal_type)
    )
    meals = meals_result.scalars().all()

    max_days = {"3day": 3, "7day": 7, "30day": 30}.get(period, 7)

    if group_by == "daily":
        price_lookup = await _build_price_lookup(db)
        days_map: dict[int, list] = {}
        for meal in meals:
            if meal.day_index > max_days:
                break
            day = days_map.setdefault(meal.day_index, [])
            ings = [
                DishIngredientItem(
                    name=ing.ingredient_name,
                    quantity_g=ing.quantity_g,
                    display=f"{round(ing.quantity_g, 0)}g" if ing.quantity_g < 1000 else f"{round(ing.quantity_g/1000, 1)}kg",
                    estimated_price=round((ing.quantity_g / 500) * price_lookup.get(ing.ingredient_name, 0), 2),
                )
                for ing in meal.ingredients
            ]
            day.append(DailyMealShoppingItem(
                meal_type=meal.meal_type,
                meal_name=meal.meal_name,
                meal_source=meal.meal_source,
                cooking_time_min=meal.cooking_time_min or 0,
                instructions=meal.instructions or "",
                dish_ingredients=ings,
            ))
        days = [
            DayShoppingGroup(day_index=idx, meals=day_meals)
            for idx, day_meals in sorted(days_map.items())
        ]
        return {"plan_id": plan_id, "period": period, "group_by": "daily", "days": days, "items": [], "item_count": 0}

    # flat mode (backward compatible)
    price_lookup = await _build_price_lookup(db)
    agg: dict[str, float] = {}
    agg_price: dict[str, float] = {}
    for meal in meals:
        if meal.day_index > max_days:
            break
        for ing in meal.ingredients:
            agg[ing.ingredient_name] = agg.get(ing.ingredient_name, 0) + ing.quantity_g
            item_price = (ing.quantity_g / 500) * price_lookup.get(ing.ingredient_name, 0)
            agg_price[ing.ingredient_name] = agg_price.get(ing.ingredient_name, 0) + item_price

    items = [{"name": k, "total_quantity_g": round(v, 1),
              "total_quantity_display": f"{round(v/500, 2)}斤" if v >= 500 else f"{round(v, 0)}g",
              "total_estimated_price": round(agg_price.get(k, 0), 2)}
             for k, v in sorted(agg.items(), key=lambda x: -x[1])]

    return {"plan_id": plan_id, "period": period, "group_by": "flat", "days": [], "items": items, "item_count": len(items)}


async def _build_plan_response(plan: MealPlan, db: AsyncSession) -> MealPlanResponse:
    result = await db.execute(
        select(DailyMeal)
        .options(selectinload(DailyMeal.ingredients))
        .where(DailyMeal.meal_plan_id == plan.id)
        .order_by(DailyMeal.day_index, DailyMeal.meal_type)
    )
    meals = result.scalars().all()

    meals_response = []
    for meal in meals:
        ingredients = [
            IngredientItem(name=ing.ingredient_name, quantity_g=ing.quantity_g)
            for ing in meal.ingredients
        ]
        meals_response.append(DailyMealResponse(
            id=meal.id, day_index=meal.day_index, meal_type=meal.meal_type,
            meal_source=meal.meal_source, meal_name=meal.meal_name,
            calories=meal.calories, protein_g=meal.protein_g,
            carbs_g=meal.carbs_g, fat_g=meal.fat_g,
            cooking_time_min=meal.cooking_time_min, instructions=meal.instructions,
            is_user_modified=meal.is_user_modified, is_user_swapped=meal.is_user_swapped,
            ingredients=ingredients,
        ))

    return MealPlanResponse(
        id=plan.id, plan_type=plan.plan_type, start_date=plan.start_date,
        end_date=plan.end_date, status=plan.status,
        calories_target=plan.calories_target, protein_target_g=plan.protein_target_g,
        carbs_target_g=plan.carbs_target_g, fat_target_g=plan.fat_target_g,
        created_at=plan.created_at, meals=meals_response,
    )


# ── Order ──
@router.post("/order/confirm", response_model=OrderResponse)
async def confirm_order(data: OrderConfirmRequest, user: User = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):
    # Verify plan belongs to user
    plan_result = await db.execute(
        select(MealPlan).where(MealPlan.id == data.plan_id, MealPlan.user_id == user.id)
    )
    if not plan_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="方案不存在")

    # Upsert: if order for this plan+day already exists, update it
    existing = await db.execute(
        select(Order).where(
            Order.meal_plan_id == data.plan_id,
            Order.day_index == data.day_index,
            Order.user_id == user.id,
        )
    )
    order = existing.scalar_one_or_none()
    if order:
        order.items_json = json.dumps(data.items, ensure_ascii=False)
        order.delivery_date = data.delivery_date
        order.status = "confirmed"
    else:
        order = Order(
            user_id=user.id,
            meal_plan_id=data.plan_id,
            day_index=data.day_index,
            delivery_date=data.delivery_date,
            status="confirmed",
            items_json=json.dumps(data.items, ensure_ascii=False),
        )
        db.add(order)
    await db.commit()
    await db.refresh(order)
    return OrderResponse.model_validate(order)


@router.get("/orders/{plan_id}", response_model=list[OrderResponse])
async def list_orders(plan_id: int, user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Order).where(
            Order.meal_plan_id == plan_id,
            Order.user_id == user.id,
            Order.status == "confirmed",
        ).order_by(Order.day_index)
    )
    return [OrderResponse.model_validate(o) for o in result.scalars().all()]


@router.delete("/order/{order_id}")
async def cancel_order(order_id: int, user: User = Depends(get_current_user),
                       db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == user.id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    # Only allow cancel if delivery is 3+ days away
    days_left = (order.delivery_date - date.today()).days
    if days_left < 3:
        raise HTTPException(status_code=400, detail="配送日在3天内，无法取消订单")
    order.status = "cancelled"
    await db.commit()
    return {"message": "已取消订单"}
