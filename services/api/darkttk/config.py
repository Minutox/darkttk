from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_secret: str = Field(
        default="local-development-only-change-me-32-chars",
        min_length=32,
    )
    database_url: str = (
        "postgresql+psycopg://darkttk:darkttk@localhost:5432/darkttk"
    )
    redis_url: str = "redis://localhost:6379/0"
    access_token_minutes: int = Field(default=15, ge=5, le=60)
    refresh_token_days: int = Field(default=30, ge=1, le=90)
    auto_create_schema: bool = True
    cors_origins: str = "http://localhost:3000"
    media_root: str = "./work/media"
    max_upload_bytes: int = Field(default=104_857_600, ge=1_048_576)
    render_mode: str = "mock"
    ffmpeg_path: str = "ffmpeg"
    render_timeout_seconds: int = Field(default=900, ge=30, le=7200)
    tiktok_mode: str = "disabled"
    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""
    tiktok_redirect_uri: str = ""
    tiktok_api_base: str = "https://open.tiktokapis.com"
    tiktok_authorize_url: str = "https://www.tiktok.com/v2/auth/authorize/"
    tiktok_app_audited: bool = False
    encryption_key: str = ""
    webhook_tolerance_seconds: int = Field(default=300, ge=60, le=900)
    publishing_max_attempts: int = Field(default=5, ge=1, le=10)
    publishing_timeout_seconds: int = Field(default=7200, ge=300, le=21_600)
    rate_limit_per_minute: int = Field(default=120, ge=10, le=10_000)
    auth_rate_limit_per_minute: int = Field(default=12, ge=3, le=120)
    trusted_proxy_hops: int = Field(default=0, ge=0, le=5)
    metrics_token: str = ""
    readiness_require_redis: bool = False
    release_version: str = "development"
    cost_monthly_limit_cents: int = Field(default=50_000, ge=0)
    cost_warning_percent: int = Field(default=80, ge=1, le=100)
    workspace_identity_secret: str = ""
    account_delivery_mode: str = "disabled"
    password_recovery_minutes: int = Field(default=30, ge=5, le=120)
    resend_api_key: str = ""
    account_email_from: str = ""
    password_recovery_url: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
