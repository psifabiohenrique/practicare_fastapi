import logging
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Body,
    File,
    HTTPException,
    UploadFile,
    status,
)

from src.routers.deps import CurrentUser, SessionDB
from src.schemas.treatment_record_schema import (
    AutomatedRecordInitializeResponse,
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
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Access denied")

    chunk_data = await audio_file.read()
    await AutomatedRecordService.save_audio_chunk(
        job_uuid, chunk_index, chunk_data
    )
    return {"status": "ok"}


@router.post("/automated-record/{job_uuid}/finalize")
async def finalize_audio_upload(
    job_uuid: UUID,
    total_chunks: int,
    db: SessionDB,
    current_user: CurrentUser,
):
    job = await AutomatedRecordService.get_job(db, job_uuid)
    if str(job.user_uuid) != str(current_user.uuid):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Access denied")

    try:
        audio_path = await AutomatedRecordService.finalize_chunked_upload(
            db, job_uuid, total_chunks
        )

        uploaded_audio = await AutomatedRecordService.upload_audio_file(
            db=db, job_uuid=job.uuid, audio_path=audio_path
        )

        transcribe_audio.apply_async(
            kwargs={"job_uuid": job.uuid, "file_name": uploaded_audio.name},
            countdown=30,
        )

        return {"status": "processing"}
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error finalizing audio upload: {e}")
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
    return await TreatmentRecordService.update_treatment_record(
        db, treatment_record_uuid, current_user.uuid, schema
    )
