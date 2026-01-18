from src.settings import settings


def init_storage_dirs():
    settings.BASE_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
