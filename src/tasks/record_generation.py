import asyncio
import logging
from uuid import UUID

from celery import current_task

from src.ai.exceptions import AIFatalError, AITransientError
from src.celery_app import celery_app
from src.database import get_async_session
from src.models.automated_record_job import JobStatus
from src.models.treatment_record_model import RecordStatus
from src.schemas.treatment_record_schema import (
    InternalTreatmentRecordUpdate,
)
from src.services.automated_record_service import AutomatedRecordService
from src.services.treatment_record_service import TreatmentRecordService

# from src.tasks.context_update import generate_context_draft_task

logger = logging.getLogger(__name__)


async def comunicate_record_fail(job_uuid: UUID, message: str):
    db = await get_async_session()
    job = await AutomatedRecordService.get_job(db, job_uuid)
    await TreatmentRecordService.update_treatment_record(
        db,
        job.treatment_record_uuid,  # type: ignore
        job.user_uuid,  # type: ignore
        InternalTreatmentRecordUpdate(content=message),
    )
    await db.close()


async def transcribe_audio_logic(job_uuid: UUID, file_name: str) -> None:
    logger.info(
        f"Iniciando transcribe_audio_logic para o job: {job_uuid}",
        extra={"job_uuid": str(job_uuid)},
    )
    db = await get_async_session()

    await AutomatedRecordService.update_job_status(
        db=db,
        job_uuid=job_uuid,
        status=JobStatus.TRANSCRIBING,
    )

    result = await AutomatedRecordService.generate_transcription(
        db, file_name, job_uuid
    )
    transcription = result.content
    if not isinstance(transcription, str) or not transcription.strip():
        logger.error(
            f"Transcrição vazia ou inválida para o job: {job_uuid}",
            extra={"job_uuid": str(job_uuid)},
        )
        raise AITransientError()

    await AutomatedRecordService.update_job_status(
        db=db,
        job_uuid=job_uuid,
        status=JobStatus.TRANSCRIBED,
        transcription=transcription,
    )
    await db.close()
    logger.info(
        f"transcribe_audio_logic concluído para o job: {job_uuid}. Disparando geração de prontuário.",  # noqa: E501
        extra={"job_uuid": str(job_uuid)},
    )
    generate_record.delay(job_uuid=job_uuid)


async def generate_record_logic(job_uuid: UUID):
    logger.info(
        f"Iniciando generate_record_logic para o job: {job_uuid}",
        extra={"job_uuid": str(job_uuid)},
    )
    db = await get_async_session()
    await AutomatedRecordService.update_job_status(
        db=db,
        job_uuid=job_uuid,
        status=JobStatus.GENERATING_RECORD,
    )

    job = await AutomatedRecordService.get_job(db, job_uuid)

    result = await AutomatedRecordService.generate_record(
        db, job.transcription, job
    )

    if (
        not result
        or not isinstance(result.content, str)
        or not result.content.strip()
    ):  # noqa: E501
        logger.error(
            f"Geração de prontuário resultou em conteúdo inválido para o job: {job_uuid}",  # noqa: E501
            extra={"job_uuid": str(job_uuid)},
        )
        raise AITransientError("Registro de prontuário em formato indevido.")

    record_text = result.content

    await TreatmentRecordService.update_treatment_record(
        db=db,
        treatment_record_uuid=job.treatment_record_uuid,  # type: ignore
        user_uuid=job.user_uuid,  # type: ignore
        schema=InternalTreatmentRecordUpdate(
            content=record_text, status=RecordStatus.READY
        ),
    )
    await AutomatedRecordService.update_job_status(
        db=db,
        job_uuid=job_uuid,
        status=JobStatus.COMPLETED,
    )
    await db.close()
    logger.info(
        f"generate_record_logic concluído com sucesso para o job: {job_uuid}",
        extra={"job_uuid": str(job_uuid)},
    )


def do_transcribe_audio(job_uuid: UUID, file_name: str):
    try:
        asyncio.run(transcribe_audio_logic(job_uuid, file_name))
    except AITransientError as e:
        asyncio.run(
            comunicate_record_fail(
                job_uuid,
                "Falha na comunicação com a IA, uma nova"
                + " tentativa será realizada em breve",
            )
        )
        logger.warning("Erro transitório ao gerar prontuário. \n" + str(e))
        raise

    except AIFatalError as e:
        asyncio.run(
            comunicate_record_fail(
                job_uuid,
                "Uma falha fatal ocorreu, tente reenviar o áudio ou"
                + " redija o prontuário manualmente.",
            )
        )
        logger.error(
            f"Erro fatal ao gerar prontuário: {str(e)}",
        )
        raise

    except Exception:
        # fallback defensivo
        asyncio.run(
            comunicate_record_fail(
                job_uuid,
                "Uma falha fatal ocorreu, tente reenviar o áudio ou"
                + " redija o prontuário manualmente.",
            )
        )
        logger.exception("Erro inesperado na task")
        raise


@celery_app.task(
    name="Gerar Transcrição",
    # bind=True,
    retry_backoff=30,
    # retry_backoff_max=60 * 60,
    autoretry_for=(AITransientError,),
    retry_kwargs={"max_retries": 10},
    acks_late=True,
)
def transcribe_audio(job_uuid: UUID, file_name: str):
    return do_transcribe_audio(job_uuid, file_name)


def do_generate_record(job_uuid: UUID, retry_count: int = 0):
    try:
        asyncio.run(generate_record_logic(job_uuid))

    except AITransientError as e:
        asyncio.run(
            comunicate_record_fail(
                job_uuid,
                "Falha na comunicação com a IA, uma nova"
                + " tentativa será realizada em breve",
            )
        )
        logger.warning(
            f"Erro transitório ao gerar prontuário. Retry: {retry_count} "
            + str(e)
        )
        raise

    except AIFatalError as e:
        asyncio.run(
            comunicate_record_fail(
                job_uuid,
                "Uma falha fatal ocorreu, tente reenviar o áudio ou"
                + " redija o prontuário manualmente.",
            )
        )
        logger.error(
            f"Erro fatal ao gerar prontuário: {str(e)}",
        )
        raise

    except Exception:
        # fallback defensivo
        asyncio.run(
            comunicate_record_fail(
                job_uuid,
                "Uma falha fatal ocorreu, tente reenviar o áudio ou"
                + " redija o prontuário manualmente.",
            )
        )
        logger.exception("Erro inesperado na task")
        raise


@celery_app.task(
    name="Gerar prontuário",
    # bind=True,
    retry_backoff=30,
    # retry_backoff_max=60 * 60,
    autoretry_for=(AITransientError,),
    retry_kwargs={"max_retries": 10},
    acks_late=True,
)
def generate_record(job_uuid: UUID):
    retry_count = 0
    if current_task and hasattr(current_task, "request"):
        retry_count = getattr(current_task.request, "retries", 0)
    return do_generate_record(job_uuid, retry_count)
