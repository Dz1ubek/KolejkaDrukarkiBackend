from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Kolejka Drukarki 3D API"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Security & JWT
    SECRET_KEY: str = "change-this-in-production-very-secret-key-32-chars-minimum"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Database
    DATABASE_URL: str = "sqlite:///./kolejka.db"

    # Initial Superuser (Admin) Seed Credentials
    FIRST_SUPERUSER_EMAIL: str = "admin@kolejka.local"
    FIRST_SUPERUSER_USERNAME: str = "admin"
    FIRST_SUPERUSER_PASSWORD: str = "AdminPassword123!"

    # File Uploads
    UPLOAD_DIR: str = "uploads/prints"
    MAX_FILE_SIZE_BYTES: int = 100 * 1024 * 1024  # 100 MB
    ALLOWED_EXTENSIONS: List[str] = [".stl", ".obj", ".3mf", ".gcode", ".step", ".stp"]

    # Pricing formula constants (in grosze/cents, e.g. 100 = 1.00 PLN)
    BASE_PRINT_FEE_GROSZE: int = 500  # 5.00 PLN
    COST_PER_GRAM_GROSZE: int = 15    # 0.15 PLN / g
    COST_PER_HOUR_GROSZE: int = 300   # 3.00 PLN / hour

    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
