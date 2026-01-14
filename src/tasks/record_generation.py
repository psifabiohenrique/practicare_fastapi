import asyncio
from uuid import UUID

from celery_app import celery_app
from database import get_async_session
from models.automated_record_job import JobStatus
from models.treatment_record_model import RecordStatus
from schemas.treatment_record_schema import (
    TreatmentRecordUpdate,
)
from services.automated_record_service import AutomatedRecordService
from services.treatment_record_service import TreatmentRecordService


async def _transcribe_audio(job_uuid: UUID, audio: bytes):
    db = await get_async_session()
    await AutomatedRecordService.update_job_status(
        db=db,
        job_uuid=job_uuid,
        status=JobStatus.TRANSCRIBING,
    )
    await asyncio.sleep(30)

    # Transcription will be implemented latter
    transcription = "Transcription"

    job = await AutomatedRecordService.get_job(db, job_uuid)

    await TreatmentRecordService.get_treatment_record(
        db=db,
        treatment_record_uuid=job.treatment_record_uuid,
        user_uuid=job.user_uuid,
    )
    await AutomatedRecordService.update_job_status(
        db=db,
        job_uuid=job_uuid,
        status=JobStatus.TRANSCRIBED,
    )
    db.close()
    generate_record.delay(job_uuid=job_uuid, transcription=transcription)


@celery_app.task(bind=True)
def transcribe_audio(self, job_uuid: UUID, audio: bytes):
    asyncio.run(_transcribe_audio(job_uuid, audio))


async def _generate_record(job_uuid: str, transcription: str):
    db = await get_async_session()
    await AutomatedRecordService.update_job_status(
        db=db,
        job_uuid=job_uuid,
        status=JobStatus.GENERATING_RECORD,
    )
    await asyncio.sleep(30)

    job = await AutomatedRecordService.get_job(db, job_uuid)

    # Record text generation will be implemented latter
    record_text = "Record text"

    await TreatmentRecordService.update_treatment_record(
        db=db,
        treatment_record_uuid=job.treatment_record_uuid,
        user_uuid=job.user_uuid,
        schema=TreatmentRecordUpdate(
            content=record_text, status=RecordStatus.READY
        ),
    )
    await AutomatedRecordService.update_job_status(
        db=db,
        job_uuid=job_uuid,
        status=JobStatus.COMPLETED,
    )
    await db.close()


@celery_app.task(bind=True)
def generate_record(self, job_uuid: str, transcription: str):
    import asyncio  # noqa: PLC0415

    asyncio.run(_generate_record(job_uuid, transcription))
