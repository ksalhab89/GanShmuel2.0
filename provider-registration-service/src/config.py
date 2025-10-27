"""Configuration settings for provider registration service"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://provider_user:provider_pass@localhost:5432/provider_registration",
        alias="DATABASE_URL"
    )

    # External services
    billing_service_url: str = "http://localhost:5002"
    redis_url: str = Field(
        default="redis://localhost:6379/1",
        alias="REDIS_URL"
    )

    # Application
    app_host: str = "0.0.0.0"
    app_port: int = 5004
    log_level: str = "INFO"

    # JWT Authentication
    jwt_secret_key: str = Field(
        default="test-secret-key-for-testing-only",
        alias="JWT_SECRET_KEY"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables


settings = Settings()
