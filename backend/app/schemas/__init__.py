from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime


class UserProfile(BaseModel):
    nickname: str = ""
    phone: str = ""
    gender: str = "unknown"
    age: int = 25
    height_cm: float = 170.0
    weight_kg: float = 70.0
    body_fat_pct: float = 20.0
    goal_type: str = "healthy"
    target_weight_kg: float = 70.0
    cooking_level: str = "medium"


class UserProfileUpdate(UserProfile):
    pass


class UserLocationUpdate(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    nickname: str
    gender: str
    age: int
    height_cm: float
    weight_kg: float
    body_fat_pct: float
    goal_type: str
    target_weight_kg: float
    cooking_level: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: str = ""
    is_admin: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class DietPreferenceInput(BaseModel):
    likes: List[str] = []
    dislikes: List[str] = []
    allergies: List[str] = []


class DietPreferenceResponse(BaseModel):
    likes: List[str]
    dislikes: List[str]
    allergies: List[str]


class LoginRequest(BaseModel):
    openid: str = Field(default="dev_test_user")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    is_new: bool = False


class MealGenerateRequest(BaseModel):
    plan_type: str = "7day"
    start_date: Optional[date] = None


class IngredientItem(BaseModel):
    name: str
    quantity_g: float = 100.0


class DailyMealResponse(BaseModel):
    id: int
    day_index: int
    meal_type: str
    meal_source: str
    meal_name: str
    calories: int
    protein_g: float
    carbs_g: float
    fat_g: float
    cooking_time_min: int
    instructions: str
    is_user_modified: bool
    is_user_swapped: bool
    ingredients: List[IngredientItem] = []

    model_config = {"from_attributes": True}


class MealPlanResponse(BaseModel):
    id: int
    plan_type: str
    start_date: Optional[date]
    end_date: Optional[date]
    status: str
    calories_target: int
    protein_target_g: float
    carbs_target_g: float
    fat_target_g: float
    created_at: datetime
    meals: List[DailyMealResponse] = []

    model_config = {"from_attributes": True}


class MealPlanSummary(BaseModel):
    id: int
    plan_type: str
    start_date: Optional[date]
    end_date: Optional[date]
    status: str
    calories_target: int
    created_at: datetime
    meal_count: int = 0

    model_config = {"from_attributes": True}


class SwapRequest(BaseModel):
    meal_id: int
    current_ingredient: str
    reason: str = ""


class SwapResponse(BaseModel):
    original: str
    alternatives: List[dict]


class SwapWarningRequest(BaseModel):
    meal_id: int
    old_ingredient: str
    new_ingredient: str


class HealthRecordInput(BaseModel):
    record_date: date
    weight_kg: Optional[float] = None
    calories_intake: int = 0
    diet_compliance: float = 0.0
    mood: str = ""
    notes: str = ""
    plan_followed: Optional[bool] = None


class HealthRecordResponse(BaseModel):
    id: int
    record_date: date
    weight_kg: Optional[float]
    calories_intake: int
    diet_compliance: float
    mood: str
    plan_followed: Optional[bool] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class IngredientResponse(BaseModel):
    id: int
    name: str
    category: str
    calories_per_100g: int
    protein_per_100g: float
    carbs_per_100g: float
    fat_per_100g: float
    estimated_price_per_500g: float
    unit: str

    model_config = {"from_attributes": True}


class MonthlyReportResponse(BaseModel):
    month: str
    weight_trend: List[dict]
    avg_compliance: float
    avg_calories: int
    suggestion: str


# ── Shopping List (Daily Grouped) ──
class DishIngredientItem(BaseModel):
    name: str
    quantity_g: float
    display: str
    estimated_price: float = 0.0


class DailyMealShoppingItem(BaseModel):
    meal_type: str
    meal_name: str
    meal_source: str = ""
    cooking_time_min: int = 0
    instructions: str = ""
    dish_ingredients: List[DishIngredientItem] = []


class DayShoppingGroup(BaseModel):
    day_index: int
    meals: List[DailyMealShoppingItem] = []


class DailyShoppingListResponse(BaseModel):
    plan_id: int
    period: str
    group_by: str
    days: List[DayShoppingGroup] = []
    # flat mode (backward compat)
    items: List[dict] = []
    item_count: int = 0


# ── Questionnaire ──
class QuestionnaireInput(BaseModel):
    cuisine_preferences: List[str] = []
    flavor_preferences: List[str] = []
    meals_per_day: int = 3
    snack_habit: str = ""
    max_cooking_time_min: int = 30
    cooking_equipment: List[str] = []
    food_allergies: List[dict] = []
    dietary_restrictions: List[str] = []
    health_conditions: List[str] = []
    weight_goal_detail: str = ""
    goal_timeline: str = ""
    additional_notes: str = ""


class QuestionnaireResponse(BaseModel):
    questionnaire_data: dict
    ai_profile_summary: str = ""


class QuestionnaireAnalysisResponse(BaseModel):
    profile_summary: str
    dietary_recommendations: List[str]
    restrictions_summary: str
    suggested_calorie_adjustment: int = 0


# ── Admin / Supermarket ──
class SupermarketCreate(BaseModel):
    name: str
    address: str = ""
    latitude: float
    longitude: float
    contact: str = ""


class SupermarketResponse(BaseModel):
    id: int
    name: str
    address: str
    latitude: float
    longitude: float
    contact: str
    is_active: bool = True
    assigned_user_count: int = 0

    model_config = {"from_attributes": True}


class SupermarketAssignmentCreate(BaseModel):
    supermarket_id: int
    user_id: int


class UserShoppingSummary(BaseModel):
    user_id: int
    nickname: str
    address: str = ""
    ingredients: List[dict] = []


class SupermarketAggregationResponse(BaseModel):
    supermarket_id: int
    supermarket_name: str
    radius_km: float
    user_count: int
    users: List[dict] = []
    total_ingredients: List[dict] = []


# ── Delivery Task ──
class DeliveryTaskStatusUpdate(BaseModel):
    status: str


class DeliveryTaskResponse(BaseModel):
    id: int
    supermarket_id: int
    supermarket_name: str = ""
    user_id: int
    user_nickname: str = ""
    user_address: str = ""
    meal_plan_id: int
    day_index: int
    delivery_date: date
    status: str
    ingredients_json: str = "[]"
    notes: str = ""
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DeliveryTaskDetailResponse(DeliveryTaskResponse):
    meal_breakdown: List[dict] = []


class DeliverySummaryResponse(BaseModel):
    supermarket_id: Optional[int] = None
    delivery_date: Optional[date] = None
    total: int = 0
    pending: int = 0
    preparing: int = 0
    shipped: int = 0
    delivered: int = 0
    cancelled: int = 0


# ── Order ──
class OrderConfirmRequest(BaseModel):
    plan_id: int
    day_index: int
    delivery_date: date
    items: List[dict] = []


class OrderResponse(BaseModel):
    id: int
    meal_plan_id: int
    day_index: int
    delivery_date: date
    status: str
    items_json: str = "[]"
    created_at: datetime

    model_config = {"from_attributes": True}
