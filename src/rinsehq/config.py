from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """Render and other hosts often provide postgres:// — SQLAlchemy needs a driver."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+psycopg://rinsehq:rinsehq@localhost:5432/rinsehq"
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_expire_minutes: int = 1440
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    seed_demo_data: bool = True
    app_base_url: str = "http://localhost:5173"

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""
    cloudinary_folder: str = "rinsehq/onboarding"

    paystack_secret_key: str = ""
    paystack_public_key: str = ""

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, value: object) -> object:
        if isinstance(value, str):
            return normalize_database_url(value)
        return value

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_local_database(self) -> bool:
        return "localhost" in self.database_url or "127.0.0.1" in self.database_url

    @property
    def smtp_password_clean(self) -> str:
        return self.smtp_password.replace(" ", "")

    @property
    def smtp_from_address(self) -> str:
        return self.smtp_from or self.smtp_user

    @property
    def cloudinary_configured(self) -> bool:
        return bool(
            self.cloudinary_cloud_name
            and self.cloudinary_api_key
            and self.cloudinary_api_secret
        )

    @property
    def paystack_configured(self) -> bool:
        return bool(self.paystack_secret_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


def validate_deployment_config(settings: Settings | None = None) -> None:
    """Fail fast on Render when DATABASE_URL was never linked."""
    settings = settings or get_settings()
    on_render = os.getenv("RENDER") == "true"
    if on_render and settings.is_local_database:
        raise RuntimeError(
            "DATABASE_URL is missing on Render — the app is using localhost:5432. "
            "Fix: open your Web Service → Environment → Add Environment Variable → "
            "select your Postgres instance (Internal Database URL). "
            "Then redeploy. Also set JWT_SECRET and SEED_DEMO_DATA=false."
        )
