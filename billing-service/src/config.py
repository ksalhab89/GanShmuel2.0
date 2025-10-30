
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database configuration
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=3307, alias="DB_PORT")
    db_user: str = Field(default="bill", alias="DB_USER")
    db_password: str = Field(default="billing_pass", alias="DB_PASSWORD")
    db_name: str = Field(default="billdb", alias="DB_NAME")

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
