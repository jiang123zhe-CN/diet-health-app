from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Safe migration: add new columns if they don't exist
    async with engine.begin() as conn:
        for col_sql in [
            "ALTER TABLE health_records ADD COLUMN plan_followed BOOLEAN",
            "ALTER TABLE users ADD COLUMN latitude FLOAT",
            "ALTER TABLE users ADD COLUMN longitude FLOAT",
            "ALTER TABLE users ADD COLUMN address VARCHAR(200) DEFAULT ''",
        ]:
            try:
                await conn.execute(text(col_sql))
            except Exception:
                pass
