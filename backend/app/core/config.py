from functools import lru_cache
from typing import Annotated, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    project_name: str = "RailFlow"
    api_v1_prefix: str = "/api/v1"
    environment: Literal["local", "staging", "production"] = "local"

    database_url: str = "postgresql+asyncpg://railway_app:railway_app_pw@localhost:5432/railway"
    migration_database_url: str = (
        "postgresql+asyncpg://railway_owner:railway_owner_pw@localhost:5432/railway"
    )

    secret_key: str = "dev-only-secret-change-me-0123456789abcdef"
    access_token_minutes: int = 30
    refresh_token_days: int = 14

    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",
        "http://localhost:8080",
    ]
    app_domain: str = "localhost"

    redis_url: str | None = None
    rate_limit_per_minute: int = 240
    auth_rate_limit_per_minute: int = 20

    stripe_webhook_secret: str | None = None

    seed_demo: bool = False
    db_echo: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @property
    def docs_enabled(self) -> bool:
        return self.environment in ("local", "staging")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
