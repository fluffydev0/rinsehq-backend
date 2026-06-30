from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

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
