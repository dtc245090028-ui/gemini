"""Cấu hình ứng dụng tập trung sử dụng Pydantic Settings."""

from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Hệ thống Quản lý Kho Thông minh AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Bảo mật & JWT
    SECRET_KEY: str = "kho-ai-secret-key-super-secure-change-in-production-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Cơ sở dữ liệu
    DATABASE_URL: str = "sqlite:///./warehouse.db"

    # Trí tuệ nhân tạo
    GEMINI_API_KEY: str = ""
    AI_PROVIDER: str = "gemini"
    AI_MODEL_NAME: str = "gemini-1.5-flash"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
