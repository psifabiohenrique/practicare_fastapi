import asyncio
import logging
import os
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    File,
    HTTPException,
    UploadFile,
    status,
)

from src.database import SessionLocal
from src.models.treatment_record_model import RecordStatus
from src.routers.deps import CurrentUser, SessionDB
from src.schemas.treatment_record_schema import (
    AutomatedRecordInitializeResponse,
    InternalTreatmentRecordUpdate,
    TreatmentRecordCreate,
    TreatmentRecordRead,
    TreatmentRecordUpdate,
)
from src.services.automated_record_service import AutomatedRecordService
from src.services.treatment_record_service import TreatmentRecordService
from src.tasks.record_generation import transcribe_audio

router = APIRouter(prefix="/treatment-records", tags=["Treatment records"])
logger = logging.getLogger(__name__)


@router.get(
    "/treatment/{treatment_uuid}", response_model=list[TreatmentRecordRead]
)
async def list_treatment_records(
    treatment_uuid: UUID,
    db: SessionDB,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> any:
    return await TreatmentRecordService.get_treatment_records(
        db, treatment_uuid, current_user.uuid, skip, limit
    )


@router.get("/{treatment_record_uuid}", response_model=TreatmentRecordRead)
async def get_treatment_record(
    treatment_record_uuid: UUID,
    db: SessionDB,
    current_user: CurrentUser,
) -> any:
    return await TreatmentRecordService.get_treatment_record(
        db, treatment_record_uuid, current_user.uuid
    )


@router.post(
    "",
    response_model=TreatmentRecordRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_treatment_record(
    schema: TreatmentRecordCreate,
    db: SessionDB,
    current_user: CurrentUser,
) -> any:
    logger.info(
        f"Criando prontuário para o tratamento: {schema.treatment_uuid}",
        extra={
            "user_uuid": str(current_user.uuid),
            "treatment_uuid": str(schema.treatment_uuid),
        },
    )
    return await TreatmentRecordService.create_treatment_record(
        db, schema, current_user.uuid
    )


@router.post(
    "/treatments/{treatment_uuid}/automated-record",
    response_model=AutomatedRecordInitializeResponse,
)
async def upload_audio(
    treatment_uuid: UUID,
    db: SessionDB,
    current_user: CurrentUser,
    session_date: Annotated[date, Body(embed=True)],
):
    logger.info(
        f"Iniciando gravação automatizada para o tratamento: {treatment_uuid}",
        extra={
            "user_uuid": str(current_user.uuid),
            "treatment_uuid": str(treatment_uuid),
            "session_date": session_date.isoformat(),
        },
    )
    record, job = await AutomatedRecordService.initialize_job(
        db=db,
        user_uuid=current_user.uuid,
        treatment_uuid=treatment_uuid,
        session_date=session_date,
    )
    return {"record": record, "job_uuid": job.uuid}


@router.post(
    "/treatments/{treatment_record_uuid}/automated-record-reload",
    response_model=AutomatedRecordInitializeResponse,
)
async def reload_audio(
    treatment_record_uuid: UUID,
    db: SessionDB,
    current_user: CurrentUser,
):
    logger.info(
        f"Recarregando áudio para o prontuário: {treatment_record_uuid}",
        extra={
            "user_uuid": str(current_user.uuid),
            "treatment_record_uuid": str(treatment_record_uuid),
        },
    )
    record, job = await AutomatedRecordService.initialize_job(
        db=db,
        user_uuid=current_user.uuid,
        treatment_record_uuid=treatment_record_uuid,
    )

    # Optional: Update record content to indicate reload
    await TreatmentRecordService.update_treatment_record(
        db,
        record.uuid,
        current_user.uuid,
        TreatmentRecordUpdate(content="Reprocessando o áudio, aguarde..."),
    )

    return {"record": record, "job_uuid": job.uuid}


@router.post("/automated-record/{job_uuid}/chunk")
async def upload_audio_chunk(
    job_uuid: UUID,
    chunk_index: int,
    db: SessionDB,
    current_user: CurrentUser,
    audio_file: UploadFile = File(...),
):
    job = await AutomatedRecordService.get_job(db, job_uuid)
    if str(job.user_uuid) != str(current_user.uuid):
        logger.warning(
            f"Acesso negado ao chunk {chunk_index} do job {job_uuid} "
            f"para o usuário {current_user.uuid}"
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Access denied")

    chunk_data = await audio_file.read()
    await AutomatedRecordService.save_audio_chunk(
        job_uuid, chunk_index, chunk_data
    )
    return {"status": "ok"}


async def process_audio_upload_background(
    job_uuid: UUID,
    audio_path: str,
):
    """
    Background task to handle audio upload with retry logic.
    """
    max_retries = 2
    retry_count = 0
    success = False

    while retry_count < max_retries and not success:
        async with SessionLocal() as db:
            try:
                # 1. Attempt upload
                uploaded_audio = (
                    await AutomatedRecordService.upload_audio_file(
                        db=db, job_uuid=job_uuid, audio_path=audio_path
                    )
                )

                # 2. Schedule transcription if successful
                transcribe_audio.apply_async(
                    kwargs={
                        "job_uuid": job_uuid,
                        "file_name": uploaded_audio.name,
                    },
                    countdown=30,
                )
                logger.info(
                    "Upload concluído e transcrição agendada para o job %s",
                    job_uuid,
                )
                success = True

            except Exception as e:
                retry_count += 1
                logger.warning(
                    f"Erro no upload de áudio (tentativa {retry_count}/{max_retries}) "  # noqa: E501
                    f"para o job {job_uuid}: {e}"
                )

                if retry_count < max_retries:
                    # Wait before retry
                    await asyncio.sleep(5)
                else:
                    # Final failure: update record with requested message
                    job = await AutomatedRecordService.get_job(db, job_uuid)
                    error_msg = (
                        "Houve um erro com o áudio enviado, por favor confira "
                        "se o áudio está correto e tente enviar novamente."
                    )

                    try:
                        await TreatmentRecordService.update_treatment_record(
                            db,
                            UUID(job.treatment_record_uuid),
                            job.user_uuid,
                            InternalTreatmentRecordUpdate(
                                content=error_msg, status=RecordStatus.FAILED
                            ),
                        )
                    except Exception as update_err:
                        logger.error(
                            f"Erro ao atualizar prontuário após falha: {update_err}"  # noqa: E501
                        )

    # Final cleanup of audio_path
    try:
        if os.path.exists(audio_path):
            os.remove(audio_path)
    except Exception as e:
        logger.warning(
            f"Falha ao deletar arquivo temporário {audio_path}: {e}"
        )  # noqa: E501


@router.post("/automated-record/{job_uuid}/finalize")
async def finalize_audio_upload(
    job_uuid: UUID,
    total_chunks: int,
    db: SessionDB,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
):
    logger.info(
        f"Finalizando upload de áudio para o job: {job_uuid}",
        extra={"job_uuid": str(job_uuid), "total_chunks": total_chunks},
    )
    job = await AutomatedRecordService.get_job(db, job_uuid)
    if str(job.user_uuid) != str(current_user.uuid):
        logger.warning(
            f"Acesso negado ao finalizar job {job_uuid} "
            f"para o usuário {current_user.uuid}"
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Access denied")

    try:
        audio_path = await AutomatedRecordService.finalize_chunked_upload(
            db, job_uuid, total_chunks
        )

        background_tasks.add_task(
            process_audio_upload_background,
            job_uuid=job.uuid,
            audio_path=audio_path,
        )

        return {"status": "processing"}
    except ValueError as e:
        logger.warning(f"Erro de validação ao finalizar upload: {e}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            f"Erro ao finalizar upload de áudio para o job {job_uuid}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar áudio: {str(e)}",
        )


@router.patch("/{treatment_record_uuid}", response_model=TreatmentRecordRead)
async def update_treatment_record(
    treatment_record_uuid: UUID,
    schema: TreatmentRecordUpdate,
    db: SessionDB,
    current_user: CurrentUser,
) -> any:
    logger.info(
        f"Atualizando prontuário: {treatment_record_uuid}",
        extra={
            "user_uuid": str(current_user.uuid),
            "treatment_record_uuid": str(treatment_record_uuid),
        },
    )
    return await TreatmentRecordService.update_treatment_record(
        db, treatment_record_uuid, current_user.uuid, schema
    )
