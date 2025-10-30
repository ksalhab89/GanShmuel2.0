"""Configuration management using Pydantic settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Application settings
    app_name: str = "Weight Service"
    @property
    def app_version(self) -> str:
        """Get version from package metadata."""
        from importlib.metadata import version
        return version("weight-service")
    debug: bool = False

    # Server settings
    host: str = "0.0.0.0"
    port: int = 5001

    # Database settings
    database_url: str = Field(
        default="mysql+aiomysql://user:password@localhost:3306/weight",
        description="Database connection URL",
    )
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_timeout: int = 30

    # CORS settings
    cors_origins: list[str] = ["*"]
    cors_credentials: bool = True
    cors_methods: list[str] = ["*"]
    cors_headers: list[str] = ["*"]

    # File upload settings
    files_directory: str = Field(
        default="/in",
        description="Directory for batch file uploads",
    )

    # Backwards compatibility alias
    @property
    def upload_dir(self) -> str:
        """Alias for files_directory for backwards compatibility."""
        return self.files_directory


settings = Settings()
