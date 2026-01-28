from pathlib import Path

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    # SECRET_KEY: str
    # ALGORITHM: str
    # ACCESS_TOKEN_EXPIRE_MINUTES: int
    # REFRESH_TOKEN_EXPIRE_MINUTES: int
    REDIS_URL: str
    ACCESS_SESSION_EXPIRE_MINUTES: int = 120
    LLM_MODEL: str
    TRANSCRIPTION_MODEL: str
    LLM_PROVIDER: str
    TRANSCRIPTION_PROVIDER: str
    GOOGLE_API_KEY: str
    OPENAI_API_KEY: str
    BASE_AUDIO_DIR: Path = Path("/data/audio")
    ALLOWED_ORIGINS: list[AnyHttpUrl] = "*"
    PRODUCTION: bool = False

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
