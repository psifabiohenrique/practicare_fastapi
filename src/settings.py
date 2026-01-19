from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_MINUTES: int
    REDIS_URL: str
    PYTHONPATH: str
    LLM_MODEL: str
    GOOGLE_API_KEY: str
    OPENAI_API_KEY: str
    BASE_AUDIO_DIR: Path = Path("/data/audio")
    ALLOWED_ORIGINS: str = "*"
    PRODUCTION: bool = False

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
