import os
from urllib.parse import urlparse

from pydantic import Field
from pydantic_settings import BaseSettings


def _parse_db_url():
    """Parse DB_URL environment variable if present."""
    db_url = os.getenv("DB_URL")
    if not db_url:
        return {}

    try:
        url = urlparse(db_url)
        return {
            "db_host": url.hostname or "localhost",
            "db_port": url.port or 3307,
            "db_user": url.username or "bill",
            "db_password": url.password or "billing_pass",
            "db_name": url.path.lstrip("/") or "billdb",
        }
    except Exception:
        return {}


_db_defaults = _parse_db_url()


class Settings(BaseSettings):
    # Database configuration
    db_host: str = Field(
        default=_db_defaults.get("db_host", "localhost"), alias="DB_HOST"
    )
    db_port: int = Field(default=_db_defaults.get("db_port", 3307), alias="DB_PORT")
    db_user: str = Field(default=_db_defaults.get("db_user", "bill"), alias="DB_USER")
    db_password: str = Field(
        default=_db_defaults.get("db_password", "billing_pass"), alias="DB_PASSWORD"
    )
    db_name: str = Field(default=_db_defaults.get("db_name", "billdb"), alias="DB_NAME")

    # Weight service configuration
    weight_service_url: str = "http://localhost:5001"
    weight_service_timeout: int = 30
    weight_service_retries: int = 3

    # File system configuration
    upload_directory: str = "/in"

    # Logging configuration
    log_level: str = "INFO"

    # Application configuration
    app_host: str = "0.0.0.0"
    app_port: int = 5002
    debug: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False
        populate_by_name = True
        extra = "ignore"  # Ignore extra environment variables


settings = Settings()
