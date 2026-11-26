from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    APP_NAME: str = "DXF to BOM Platform"

    APP_VERSION: str = "0.1.0"

    ENVIRONMENT: str = "development"

    SECRET_KEY: str

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 1

    DATABASE_URL: str

    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://192.168.1.77:3000",
    ]
    # Add trusted public frontend origins through the deployment environment.
    CORS_ORIGIN_REGEX: str | None = None

    # Drawing storage
    STORAGE_BACKEND: str = "local"
    LOCAL_STORAGE_PATH: str = "./storage/drawings"

    MAX_DXF_FILE_SIZE_MB: int = 100

    REDIS_URL: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS]


settings = Settings()