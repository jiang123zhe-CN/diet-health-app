import json
import math
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.meal_plan import MealPlan, DailyMeal, MealIngredient
from app.models.ingredient import Ingredient
from app.models.supermarket import Supermarket, SupermarketAssignment
from app.models.delivery import DeliveryTask
from app.schemas import (
    IngredientResponse, UserResponse,
    SupermarketCreate, SupermarketResponse, SupermarketAssignmentCreate,
    SupermarketAggregationResponse,
    DeliveryTaskStatusUpdate, DeliveryTaskResponse, DeliveryTaskDetailResponse,
    DeliverySummaryResponse,
)

router = APIRouter(prefix="/api/v1/admin", tags=["管理后台"])


async def verify_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


@router.get("/users", response_model=list[UserResponse])
async def list_users(limit: int = 50, offset: int = 0, admin: User = Depends(verify_admin),
                     db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
    )
    return [UserResponse.model_validate(u) for u in result.scalars().all()]


@router.get("/stats")
async def get_stats(admin: User = Depends(verify_admin), db: AsyncSession = Depends(get_db)):
    user_count = (await db.execute(select(func.count(User.id)))).scalar()
    plan_count = (await db.execute(select(func.count(MealPlan.id)))).scalar()
    ingredient_count = (await db.execute(
        select(func.count(Ingredient.id)).where(Ingredient.is_active == True)
    )).scalar()
    supermarket_count = (await db.execute(select(func.count(Supermarket.id)))).scalar()
    return {
        "total_users": user_count, "total_meal_plans": plan_count,
        "total_ingredients": ingredient_count, "total_supermarkets": supermarket_count,
    }


# ── Ingredient CRUD ──
@router.get("/ingredients", response_model=list[IngredientResponse])
async def list_ingredients(search: str = Query(default=""), admin: User = Depends(verify_admin),
                           db: AsyncSession = Depends(get_db)):
    q = select(Ingredient).order_by(Ingredient.category, Ingredient.name)
    if search:
        q = q.where(Ingredient.name.contains(search))
    result = await db.execute(q)
    return [IngredientResponse.model_validate(r) for r in result.scalars().all()]


@router.post("/ingredient", response_model=IngredientResponse)
async def create_ingredient(data: dict, admin: User = Depends(verify_admin),
                            db: AsyncSession = Depends(get_db)):
    ingredient = Ingredient(**data)
    db.add(ingredient)
    await db.commit()
    await db.refresh(ingredient)
    return IngredientResponse.model_validate(ingredient)


@router.put("/ingredient/{id}", response_model=IngredientResponse)
async def update_ingredient(id: int, data: dict, admin: User = Depends(verify_admin),
                            db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Ingredient).where(Ingredient.id == id))
    ingredient = result.scalar_one_or_none()
    if not ingredient:
        raise HTTPException(status_code=404, detail="食材不存在")
    for field, value in data.items():
        if hasattr(ingredient, field):
            setattr(ingredient, field, value)
    await db.commit()
    await db.refresh(ingredient)
    return IngredientResponse.model_validate(ingredient)


@router.delete("/ingredient/{id}")
async def delete_ingredient(id: int, admin: User = Depends(verify_admin),
                            db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Ingredient).where(Ingredient.id == id))
    ingredient = result.scalar_one_or_none()
    if not ingredient:
        raise HTTPException(status_code=404, detail="食材不存在")
    ingredient.is_active = False
    await db.commit()
    return {"message": "已下架"}


# ── Supermarket CRUD ──
@router.get("/supermarkets", response_model=list[SupermarketResponse])
async def list_supermarkets(admin: User = Depends(verify_admin),
                            db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Supermarket).order_by(Supermarket.name))
    supermarkets = result.scalars().all()
    out = []
    for s in supermarkets:
        count = (await db.execute(
            select(func.count(SupermarketAssignment.id))
            .where(SupermarketAssignment.supermarket_id == s.id)
        )).scalar()
        out.append(SupermarketResponse(
            id=s.id, name=s.name, address=s.address, latitude=s.latitude,
            longitude=s.longitude, contact=s.contact, is_active=s.is_active,
            assigned_user_count=count,
        ))
    return out


@router.post("/supermarket", response_model=SupermarketResponse)
async def create_supermarket(data: SupermarketCreate, admin: User = Depends(verify_admin),
                              db: AsyncSession = Depends(get_db)):
    s = Supermarket(**data.model_dump())
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return SupermarketResponse(
        id=s.id, name=s.name, address=s.address, latitude=s.latitude,
        longitude=s.longitude, contact=s.contact, is_active=s.is_active,
        assigned_user_count=0,
    )


# ── Assignment ──
@router.post("/supermarket/assign")
async def assign_user(data: SupermarketAssignmentCreate, admin: User = Depends(verify_admin),
                      db: AsyncSession = Depends(get_db)):
    existing = await db.execute(
        select(SupermarketAssignment)
        .where(SupermarketAssignment.supermarket_id == data.supermarket_id,
               SupermarketAssignment.user_id == data.user_id)
    )
    if existing.scalar_one_or_none():
        return {"message": "已分配"}
    assignment = SupermarketAssignment(supermarket_id=data.supermarket_id, user_id=data.user_id)
    db.add(assignment)
    await db.commit()
    return {"message": "分配成功"}


@router.delete("/supermarket/assign/{assignment_id}")
async def remove_assignment(assignment_id: int, admin: User = Depends(verify_admin),
                             db: AsyncSession = Depends(get_db)):
    await db.execute(delete(SupermarketAssignment).where(SupermarketAssignment.id == assignment_id))
    await db.commit()
    return {"message": "已取消分配"}


@router.get("/supermarket/{id}/assignments")
async def list_assignments(id: int, admin: User = Depends(verify_admin),
                            db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SupermarketAssignment, User.nickname, User.address)
        .join(User, SupermarketAssignment.user_id == User.id)
        .where(SupermarketAssignment.supermarket_id == id)
    )
    rows = result.all()
    return [{"assignment_id": row[0].id, "user_id": row[0].user_id,
             "nickname": row[1], "address": row[2],
             "assigned_at": str(row[0].assigned_at)} for row in rows]


# ── Aggregation ──
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@router.get("/supermarket/{id}/aggregate")
async def aggregate_shopping(id: int, radius_km: float = Query(3.0),
                              admin: User = Depends(verify_admin),
                              db: AsyncSession = Depends(get_db)):
    # Get supermarket
    result = await db.execute(select(Supermarket).where(Supermarket.id == id))
    supermarket = result.scalar_one_or_none()
    if not supermarket:
        raise HTTPException(status_code=404, detail="商超不存在")

    # Get all assignments for this supermarket
    assign_result = await db.execute(
        select(SupermarketAssignment).where(SupermarketAssignment.supermarket_id == id)
    )
    assignments = assign_result.scalars().all()

    users_data = []
    total_agg: dict[str, float] = {}

    for assignment in assignments:
        user_result = await db.execute(select(User).where(User.id == assignment.user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            continue

        # Check distance
        if user.latitude is None or user.longitude is None:
            continue
        dist = haversine_km(supermarket.latitude, supermarket.longitude,
                           user.latitude, user.longitude)
        if dist > radius_km:
            continue

        # Get active meal plan
        plan_result = await db.execute(
            select(MealPlan)
            .where(MealPlan.user_id == user.id)
            .order_by(MealPlan.created_at.desc()).limit(1)
        )
        plan = plan_result.scalar_one_or_none()
        if not plan:
            continue

        # Get ingredients
        meals_result = await db.execute(
            select(DailyMeal).options(selectinload(DailyMeal.ingredients))
            .where(DailyMeal.meal_plan_id == plan.id)
        )
        meals = meals_result.scalars().all()

        user_ingredients: dict[str, float] = {}
        for meal in meals:
            for ing in meal.ingredients:
                name = ing.ingredient_name
                user_ingredients[name] = user_ingredients.get(name, 0) + ing.quantity_g
                total_agg[name] = total_agg.get(name, 0) + ing.quantity_g

        users_data.append({
            "user_id": user.id,
            "nickname": user.nickname,
            "address": user.address or "",
            "distance_km": round(dist, 2),
            "ingredients": [{"name": k, "total_quantity_g": round(v, 1),
                           "display": f"{round(v/500,2)}斤" if v>=500 else f"{round(v,0)}g"}
                          for k, v in sorted(user_ingredients.items(), key=lambda x: -x[1])],
        })

    total_items = [{"name": k, "total_quantity_g": round(v, 1),
                    "display": f"{round(v/500,2)}斤" if v>=500 else f"{round(v,0)}g"}
                   for k, v in sorted(total_agg.items(), key=lambda x: -x[1])]

    return SupermarketAggregationResponse(
        supermarket_id=supermarket.id,
        supermarket_name=supermarket.name,
        radius_km=radius_km,
        user_count=len(users_data),
        users=users_data,
        total_ingredients=total_items,
    )


# ── Delivery Task Management ──
async def _build_delivery_response(task: DeliveryTask, db: AsyncSession) -> DeliveryTaskResponse:
    u_result = await db.execute(select(User).where(User.id == task.user_id))
    user = u_result.scalar_one_or_none()
    s_result = await db.execute(select(Supermarket).where(Supermarket.id == task.supermarket_id))
    sm = s_result.scalar_one_or_none()
    return DeliveryTaskResponse(
        id=task.id, supermarket_id=task.supermarket_id,
        supermarket_name=sm.name if sm else "",
        user_id=task.user_id, user_nickname=user.nickname if user else "",
        user_address=user.address if user else "",
        meal_plan_id=task.meal_plan_id, day_index=task.day_index,
        delivery_date=task.delivery_date, status=task.status,
        ingredients_json=task.ingredients_json or "[]",
        notes=task.notes or "", created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.get("/delivery/tasks", response_model=list[DeliveryTaskResponse])
async def list_delivery_tasks(supermarket_id: int = Query(default=None),
                              status: str = Query(default=""),
                              date: str = Query(default=""),
                              limit: int = Query(default=100), offset: int = Query(default=0),
                              admin: User = Depends(verify_admin),
                              db: AsyncSession = Depends(get_db)):
    q = select(DeliveryTask)
    if supermarket_id:
        q = q.where(DeliveryTask.supermarket_id == supermarket_id)
    if status:
        q = q.where(DeliveryTask.status == status)
    if date:
        q = q.where(DeliveryTask.delivery_date == date)
    q = q.order_by(DeliveryTask.delivery_date.desc(), DeliveryTask.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    tasks = result.scalars().all()
    return [await _build_delivery_response(t, db) for t in tasks]


@router.post("/delivery/generate")
async def generate_delivery_tasks(supermarket_id: int = Query(default=None),
                                  delivery_date: str = Query(default=""),
                                  admin: User = Depends(verify_admin),
                                  db: AsyncSession = Depends(get_db)):
    assign_q = select(SupermarketAssignment)
    if supermarket_id:
        assign_q = assign_q.where(SupermarketAssignment.supermarket_id == supermarket_id)
    assign_result = await db.execute(assign_q)
    assignments = assign_result.scalars().all()

    tasks_created = 0
    for assignment in assignments:
        user_result = await db.execute(select(User).where(User.id == assignment.user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            continue
        plan_result = await db.execute(
            select(MealPlan).where(MealPlan.user_id == user.id, MealPlan.status == "active")
            .order_by(MealPlan.created_at.desc()).limit(1)
        )
        plan = plan_result.scalar_one_or_none()
        if not plan:
            continue

        total_days = {"3day": 3, "7day": 7, "30day": 30}.get(plan.plan_type, 7)
        for day_idx in range(1, total_days + 1):
            existing = await db.execute(
                select(DeliveryTask).where(
                    DeliveryTask.supermarket_id == assignment.supermarket_id,
                    DeliveryTask.user_id == assignment.user_id,
                    DeliveryTask.meal_plan_id == plan.id,
                    DeliveryTask.day_index == day_idx,
                )
            )
            if existing.scalar_one_or_none():
                continue

            meals_result = await db.execute(
                select(DailyMeal).options(selectinload(DailyMeal.ingredients))
                .where(DailyMeal.meal_plan_id == plan.id, DailyMeal.day_index == day_idx)
                .order_by(DailyMeal.meal_type)
            )
            meals = meals_result.scalars().all()
            if not meals:
                continue

            snapshot = []
            for meal in meals:
                snapshot.append({
                    "meal_type": meal.meal_type, "meal_name": meal.meal_name,
                    "ingredients": [{"name": ing.ingredient_name, "quantity_g": ing.quantity_g}
                                    for ing in meal.ingredients],
                })

            task_date = None
            if delivery_date:
                task_date = date.fromisoformat(delivery_date)
            elif plan.start_date:
                task_date = plan.start_date + timedelta(days=day_idx - 1)
            else:
                task_date = date.today() + timedelta(days=day_idx - 1)

            task = DeliveryTask(
                supermarket_id=assignment.supermarket_id, user_id=user.id,
                meal_plan_id=plan.id, day_index=day_idx, delivery_date=task_date,
                status="pending", ingredients_json=json.dumps(snapshot, ensure_ascii=False),
            )
            db.add(task)
            tasks_created += 1

    await db.commit()
    return {"tasks_created": tasks_created}


@router.put("/delivery/task/{id}/status", response_model=DeliveryTaskResponse)
async def update_delivery_status(id: int, data: DeliveryTaskStatusUpdate,
                                 admin: User = Depends(verify_admin),
                                 db: AsyncSession = Depends(get_db)):
    valid = {"pending", "preparing", "shipped", "delivered", "cancelled"}
    if data.status not in valid:
        raise HTTPException(status_code=400, detail=f"无效状态，可选: {', '.join(sorted(valid))}")
    result = await db.execute(select(DeliveryTask).where(DeliveryTask.id == id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="配送任务不存在")
    task.status = data.status
    await db.commit()
    await db.refresh(task)
    return await _build_delivery_response(task, db)


@router.get("/delivery/task/{id}", response_model=DeliveryTaskDetailResponse)
async def get_delivery_task_detail(id: int, admin: User = Depends(verify_admin),
                                   db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DeliveryTask).where(DeliveryTask.id == id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="配送任务不存在")
    base = await _build_delivery_response(task, db)
    meal_breakdown = json.loads(task.ingredients_json or "[]")
    return DeliveryTaskDetailResponse(
        **base.model_dump(), meal_breakdown=meal_breakdown,
    )


@router.get("/delivery/summary", response_model=DeliverySummaryResponse)
async def delivery_summary(supermarket_id: int = Query(default=None),
                           date: str = Query(default=""),
                           admin: User = Depends(verify_admin),
                           db: AsyncSession = Depends(get_db)):
    async def _count(st: str) -> int:
        q = select(func.count(DeliveryTask.id))
        if supermarket_id:
            q = q.where(DeliveryTask.supermarket_id == supermarket_id)
        if date:
            q = q.where(DeliveryTask.delivery_date == date)
        if st:
            q = q.where(DeliveryTask.status == st)
        result = await db.execute(q)
        return result.scalar() or 0

    return DeliverySummaryResponse(
        supermarket_id=supermarket_id,
        delivery_date=date.fromisoformat(date) if date else None,
        total=await _count(""),
        pending=await _count("pending"),
        preparing=await _count("preparing"),
        shipped=await _count("shipped"),
        delivered=await _count("delivered"),
        cancelled=await _count("cancelled"),
    )
