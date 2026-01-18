import uuid
import aiofiles

from pathlib import Path
from uuid import UUID

from src.settings import settings


class AudioStorageService:
    @staticmethod
    def get_job_dir(job_uuid: UUID) -> Path:
        path = settings.BASE_AUDIO_DIR / str(job_uuid)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    async def save_upload(
        job_uuid: UUID,
        upload_file,
    ) -> Path:
        job_dir = AudioStorageService.get_job_dir(job_uuid)

        suffix = Path(upload_file.filename).suffix or ".webm"
        file_path = job_dir / f"{uuid.uuid4()}{suffix}"

        async with aiofiles.open(file_path, "wb") as f:
            while chunk := await upload_file.read(1024 * 1024):
                await f.write(chunk)

        return file_path

    @staticmethod
    def remove_file(path: Path):
        try:
            path.unlink(missing_ok=True)
            path.parent.rmdir()  # remove pasta do job
        except OSError:
            pass  # defensivo, não falha task
