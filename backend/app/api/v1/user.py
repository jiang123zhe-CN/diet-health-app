from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import create_access_token, get_current_user
from app.models.user import User
from app.models.diet_preference import UserDietPreference
from app.models.diet_profile import UserDietProfile
from app.schemas import (
    LoginRequest, TokenResponse, UserProfile, UserProfileUpdate,
    UserResponse, UserLocationUpdate, DietPreferenceInput, DietPreferenceResponse,
    QuestionnaireInput, QuestionnaireResponse, QuestionnaireAnalysisResponse,
)
from app.services.ai_service import build_questionnaire_analysis_prompt, call_deepseek, extract_json

router = APIRouter(prefix="/api/v1/user", tags=["用户"])


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.openid == req.openid))
    user = result.scalar_one_or_none()
    is_new = False
    if user is None:
        user = User(openid=req.openid, nickname=f"用户{req.openid[:6]}")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        is_new = True
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user), is_new=is_new)


@router.get("/profile", response_model=UserResponse)
async def get_profile(user: User = Depends(get_current_user)):
    return UserResponse.model_validate(user)


@router.put("/profile", response_model=UserResponse)
async def update_profile(data: UserProfileUpdate, user: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    for field, value in data.model_dump().items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.get("/preferences", response_model=DietPreferenceResponse)
async def get_preferences(user: User = Depends(get_current_user),
                          db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(UserDietPreference).where(UserDietPreference.user_id == user.id)
    )
    prefs = result.scalars().all()
    likes = [p.item_name for p in prefs if p.preference_type == "like"]
    dislikes = [p.item_name for p in prefs if p.preference_type == "dislike"]
    allergies = [p.item_name for p in prefs if p.preference_type == "allergy"]
    return DietPreferenceResponse(likes=likes, dislikes=dislikes, allergies=allergies)


@router.put("/preferences", response_model=DietPreferenceResponse)
async def update_preferences(data: DietPreferenceInput, user: User = Depends(get_current_user),
                             db: AsyncSession = Depends(get_db)):
    await db.execute(delete(UserDietPreference).where(UserDietPreference.user_id == user.id))
    for name in data.likes:
        db.add(UserDietPreference(user_id=user.id, preference_type="like", item_name=name))
    for name in data.dislikes:
        db.add(UserDietPreference(user_id=user.id, preference_type="dislike", item_name=name))
    for name in data.allergies:
        db.add(UserDietPreference(user_id=user.id, preference_type="allergy", item_name=name))
    await db.commit()
    return DietPreferenceResponse(likes=data.likes, dislikes=data.dislikes, allergies=data.allergies)


# ── Questionnaire ──
@router.get("/questionnaire", response_model=QuestionnaireResponse)
async def get_questionnaire(user: User = Depends(get_current_user),
                            db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(UserDietProfile).where(UserDietProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        return QuestionnaireResponse(questionnaire_data={}, ai_profile_summary="")
    return QuestionnaireResponse(
        questionnaire_data=profile.questionnaire_data or {},
        ai_profile_summary=profile.ai_profile_summary or "",
    )


@router.put("/questionnaire", response_model=QuestionnaireResponse)
async def save_questionnaire(data: QuestionnaireInput,
                             user: User = Depends(get_current_user),
                             db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(UserDietProfile).where(UserDietProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = UserDietProfile(user_id=user.id, questionnaire_data=data.model_dump())
        db.add(profile)
    else:
        profile.questionnaire_data = data.model_dump()
    await db.commit()
    await db.refresh(profile)
    return QuestionnaireResponse(
        questionnaire_data=profile.questionnaire_data or {},
        ai_profile_summary=profile.ai_profile_summary or "",
    )


@router.post("/questionnaire/analyze", response_model=QuestionnaireAnalysisResponse)
async def analyze_questionnaire(user: User = Depends(get_current_user),
                                db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(UserDietProfile).where(UserDietProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=400, detail="请先填写问卷")

    user_data = {
        "age": user.age, "gender": user.gender,
        "height_cm": user.height_cm, "weight_kg": user.weight_kg,
        "goal_type": user.goal_type,
    }
    prompt = build_questionnaire_analysis_prompt(profile.questionnaire_data or {}, user_data)
    raw = await call_deepseek(prompt, "分析问卷", max_tokens=2000)
    data = extract_json(raw)

    profile.ai_profile_summary = data.get("profile_summary", "")
    await db.commit()

    return QuestionnaireAnalysisResponse(
        profile_summary=data.get("profile_summary", ""),
        dietary_recommendations=data.get("dietary_recommendations", []),
        restrictions_summary=data.get("restrictions_summary", ""),
        suggested_calorie_adjustment=data.get("suggested_calorie_adjustment", 0),
    )


# ── Location ──
@router.put("/location")
async def update_location(data: UserLocationUpdate, user: User = Depends(get_current_user),
                           db: AsyncSession = Depends(get_db)):
    if data.latitude is not None:
        user.latitude = data.latitude
    if data.longitude is not None:
        user.longitude = data.longitude
    if data.address is not None:
        user.address = data.address
    await db.commit()
    return {"message": "位置已更新", "latitude": user.latitude, "longitude": user.longitude, "address": user.address}
