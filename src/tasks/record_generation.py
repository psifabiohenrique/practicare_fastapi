import asyncio
import logging
from uuid import UUID

from ai.chains.record_generation import RecordGenerationChain
from ai.chains.transcription import TranscriptionChain
from ai.exceptions import AIFatalError, AITransientError
from celery_app import celery_app
from database import get_async_session
from models.automated_record_job import JobStatus
from models.treatment_record_model import RecordStatus
from schemas.treatment_record_schema import (
    TreatmentRecordUpdate,
)
from services.automated_record_service import AutomatedRecordService
from services.treatment_record_service import TreatmentRecordService

logger = logging.getLogger(__name__)


async def _transcribe_audio(job_uuid: UUID, audio: bytes):
    db = await get_async_session()
    await AutomatedRecordService.update_job_status(
        db=db,
        job_uuid=job_uuid,
        status=JobStatus.TRANSCRIBING,
    )

    transcription_chain = TranscriptionChain()
    try:
        transcription = await transcription_chain.transcribe(audio_bytes=audio)
        logger.info(f"Transcrição: {transcription}")
    except Exception as e:
        await AutomatedRecordService.update_job_status(
            db=db,
            job_uuid=job_uuid,
            status=JobStatus.FAILED,
        )
        await db.close()
        raise e

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
    await db.close()
    generate_record.delay(job_uuid=job_uuid, transcription=transcription)


async def _generate_record(job_uuid: str, transcription: str):
    db = await get_async_session()
    await AutomatedRecordService.update_job_status(
        db=db,
        job_uuid=job_uuid,
        status=JobStatus.GENERATING_RECORD,
    )

    # AI Integration for record generation
    record_chain = RecordGenerationChain()
    try:
        record_text = await record_chain.generate(transcription=transcription)
        logger.info(f"Record text: {record_text}")
    except Exception as e:
        await AutomatedRecordService.update_job_status(
            db=db,
            job_uuid=job_uuid,
            status=JobStatus.FAILED,
        )
        await db.close()
        raise e

    job = await AutomatedRecordService.get_job(db, job_uuid)

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


@celery_app.task(
    name="Gerar Transcrição",
    bind=True,
    retry_backoff=30,
    retry_backoff_max=60 * 60,
    autoretry_for=(AITransientError,),
    retry_kwargs={"max_retries": 10},
)
def transcribe_audio(self, job_uuid: UUID, audio: bytes):
    try:
        asyncio.run(_transcribe_audio(job_uuid, audio))
    except AITransientError as e:
        logger.warning(
            f"Erro transitório ao gerar prontuário. {self.request.retry} \n"
            + str(e)
        )
        raise

    except AIFatalError as e:
        logger.error(
            f"Erro fatal ao gerar prontuário: {str(e)}",
        )
        raise

    except Exception:
        # fallback defensivo
        logger.exception("Erro inesperado na task")
        raise


@celery_app.task(
    name="Gerar prontuário",
    bind=True,
    retry_backoff=30,
    retry_backoff_max=60 * 60,
    autoretry_for=(AITransientError,),
    retry_kwargs={"max_retries": 10},
)
def generate_record(self, job_uuid: str, transcription: str):
    try:
        asyncio.run(_generate_record(job_uuid, transcription))

    except AITransientError as e:
        logger.warning(
            f"Erro transitório ao gerar prontuário. {self.request.retry}"
            + str(e)
        )
        raise

    except AIFatalError as e:
        logger.error(
            f"Erro fatal ao gerar prontuário: {str(e)}",
        )
        raise

    except Exception:
        # fallback defensivo
        logger.exception("Erro inesperado na task")
        raise
