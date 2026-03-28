from pathlib import Path

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str = "change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080
    REDIS_URL: str
    ACCESS_SESSION_EXPIRE_MINUTES: int = 120
    LLM_MODEL: str
    TRANSCRIPTION_MODEL: str
    LLM_PROVIDER: str
    TRANSCRIPTION_PROVIDER: str
    GOOGLE_API_KEY: str
    OPENAI_API_KEY: str
    BASE_AUDIO_DIR: Path = Path("/data/audio")
    LOG_DIR: Path = Path("/data/logs")
    LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT: int = 5
    LOG_LEVEL: str = "INFO"
    ALLOWED_ORIGINS: list[AnyHttpUrl] = "*"
    PRODUCTION: bool = False

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
