from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.health_record import HealthRecord
from app.schemas import HealthRecordInput, HealthRecordResponse, MonthlyReportResponse
from app.services.ai_service import build_monthly_report_prompt, call_deepseek, extract_json

router = APIRouter(prefix="/api/v1/health", tags=["健康记录"])


@router.post("/record", response_model=HealthRecordResponse)
async def create_record(data: HealthRecordInput, user: User = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):
    record = HealthRecord(user_id=user.id, **data.model_dump())
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return HealthRecordResponse.model_validate(record)


@router.get("/records", response_model=list[HealthRecordResponse])
async def get_records(days: int = 30, user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    cutoff = date.today() - timedelta(days=days)
    result = await db.execute(
        select(HealthRecord)
        .where(HealthRecord.user_id == user.id, HealthRecord.record_date >= cutoff)
        .order_by(HealthRecord.record_date.desc())
    )
    records = result.scalars().all()
    return [HealthRecordResponse.model_validate(r) for r in records]


@router.get("/report/monthly", response_model=MonthlyReportResponse)
async def monthly_report(user: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    cutoff = date.today() - timedelta(days=30)
    result = await db.execute(
        select(HealthRecord)
        .where(HealthRecord.user_id == user.id, HealthRecord.record_date >= cutoff)
        .order_by(HealthRecord.record_date.asc())
    )
    records = result.scalars().all()

    if len(records) < 3:
        raise HTTPException(status_code=400, detail="数据不足，至少需要3天记录才能生成报告")

    weight_trend = [{"date": str(r.record_date), "weight": r.weight_kg or user.weight_kg}
                    for r in records if r.weight_kg]
    avg_compliance = sum(r.diet_compliance for r in records) / len(records) if records else 0
    avg_calories = int(sum(r.calories_intake for r in records) / len(records)) if records else 0

    records_data = [{"date": str(r.record_date), "weight": r.weight_kg, "calories": r.calories_intake,
                     "compliance": r.diet_compliance, "mood": r.mood}
                    for r in records[-30:]]
    user_profile = {"goal_type": user.goal_type, "weight_kg": user.weight_kg}
    prompt = build_monthly_report_prompt(records_data, user_profile)
    raw = await call_deepseek(prompt, "生成月度报告", max_tokens=2000)
    data = extract_json(raw)

    return MonthlyReportResponse(
        month=date.today().strftime("%Y-%m"),
        weight_trend=weight_trend,
        avg_compliance=round(avg_compliance, 1),
        avg_calories=avg_calories,
        suggestion=data.get("suggestions", data.get("summary", "保持当前方案")),
    )
