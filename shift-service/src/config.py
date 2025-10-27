"""Configuration settings for shift service."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # Application
    app_name: str = "Shift Service"
    app_version: str = "1.0.0"
    debug: bool = False

    # Database
    database_url: str = "mysql+pymysql://shift_user:shift_pass@shift-db:3306/shift_management"

    # Redis
    redis_url: str = "redis://shift-redis:6379/0"

    # External Services
    weight_service_url: str = "http://weight-service:5001"
    billing_service_url: str = "http://billing-service:5002"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://frontend:3000"]
    cors_credentials: bool = True
    cors_methods: list[str] = ["*"]
    cors_headers: list[str] = ["*"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
