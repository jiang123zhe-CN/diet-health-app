from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Diet Health App"
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite+aiosqlite:///./diet_health.db"
    JWT_SECRET: str = "dev-secret-change-in-production-xxx"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 720
    QWEN_API_KEY: str = ""
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_MODEL: str = "qwen-plus"
    STATIC_DIR: str = "static"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
