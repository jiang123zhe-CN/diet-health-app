import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.database import init_db, async_session
from app.models.ingredient import Ingredient
from app.models.health_record import HealthRecord
from app.models.diet_profile import UserDietProfile
from app.models.supermarket import Supermarket, SupermarketAssignment
from app.models.delivery import DeliveryTask
from app.models.order import Order
from seed_data.ingredients import SEED_INGREDIENTS
from sqlalchemy import select


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Seed ingredient data
    async with async_session() as db:
        result = await db.execute(select(Ingredient).limit(1))
        if result.scalar_one_or_none() is None:
            for item in SEED_INGREDIENTS:
                db.add(Ingredient(**item))
            await db.commit()
    yield


app = FastAPI(title=settings.APP_NAME, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

from app.api.v1.user import router as user_router
from app.api.v1.meal import router as meal_router
from app.api.v1.health import router as health_router
from app.api.v1.ingredient import router as ingredient_router
from app.api.v1.admin import router as admin_router

app.include_router(user_router)
app.include_router(meal_router)
app.include_router(health_router)
app.include_router(ingredient_router)
app.include_router(admin_router)

app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")


FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend")


@app.get("/")
async def serve_frontend():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/admin")
async def serve_admin():
    return FileResponse(os.path.join(FRONTEND_DIR, "admin.html"))


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME}
