import shutil
import tempfile
from datetime import date
from http import HTTPStatus
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

from src.routers.deps import CurrentUser, SessionDB
from src.schemas.treatment_record_schema import (
    TreatmentRecordCreate,
    TreatmentRecordRead,
    TreatmentRecordUpdate,
)
from src.services.automated_record_service import AutomatedRecordService
from src.services.treatment_record_service import TreatmentRecordService
from src.services.treatment_service import TreatmentService
from src.tasks.record_generation import transcribe_audio

router = APIRouter(prefix="/treatment-records", tags=["Treatment records"])


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
    response_model=TreatmentRecordRead,
)
async def upload_audio(  # noqa: PLR0913, PLR0917
    treatment_uuid: UUID,
    db: SessionDB,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    session_date: Annotated[date, Body()],
    audio_file: UploadFile = File(...),
):

    user_uuid = current_user.uuid

    content_type = audio_file.content_type.split(";")[0]

    if content_type not in {
        "audio/webm",
        "video/webm",
        "audio/ogg",
        "audio/mpeg",
        "audio/mp3",
        "audio/wav",
    }:
        raise HTTPException(
            HTTPStatus.BAD_REQUEST, detail="Invalid audio content type"
        )

    treatment = await TreatmentService.get_treatment_by_uuid(
        db=db, treatment_uuid=treatment_uuid, user_uuid=user_uuid
    )
    record = await TreatmentRecordService.create_treatment_record(
        db=db,
        schema=TreatmentRecordCreate(
            treatment_uuid=treatment_uuid,
            date=session_date,
            start_time=treatment.start_time,
            end_time=treatment.end_time,
            content="Processando áudio e gerando prontuário...",
        ),
        user_uuid=user_uuid,
    )

    job = await AutomatedRecordService.create_job(
        db=db,
        treatment_uuid=treatment_uuid,
        user_uuid=user_uuid,
        treatment_record_uuid=record.uuid,
    )

    # Save audio temporarily to disk
    audio_path = f"audio_{job.uuid}.webm"
    with open(audio_path, "wb") as f:
        # f.write(await audio_file.read())
        shutil.copyfileobj(audio_file.file, f)
    await audio_file.close()
    del audio_file
    uploaded_audio = await AutomatedRecordService.upload_audio_file(
        db=db, job_uuid=job.uuid, audio_path=audio_path
    )

    transcribe_audio.apply_async(
        kwargs={"job_uuid": job.uuid, "file_name": uploaded_audio.name},
        countdown=30,
    )

    return record


@router.post(
    "/treatments/{treatment_record_uuid}/automated-record-reload",
    response_model=TreatmentRecordRead,
)
async def reload_audio(
    treatment_record_uuid: UUID,
    db: SessionDB,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    audio_file: UploadFile = File(...),
):

    user_uuid = current_user.uuid

    content_type = audio_file.content_type.split(";")[0]
    if content_type not in {
        "audio/webm",
        "video/webm",
        "audio/ogg",
        "audio/mpeg",
        "audio/mp3",
        "audio/wav",
    }:
        raise HTTPException(
            HTTPStatus.BAD_REQUEST, detail="Invalid audio content type"
        )

    record = await TreatmentRecordService.get_treatment_record(
        db=db, treatment_record_uuid=treatment_record_uuid, user_uuid=user_uuid
    )

    job = await AutomatedRecordService.create_job(
        db=db,
        treatment_uuid=record.treatment_uuid,
        user_uuid=user_uuid,
        treatment_record_uuid=record.uuid,
    )

    # Save audio temporarily to disk
    with tempfile.TemporaryDirectory() as temp_dir:
        audio_path = f"{temp_dir}/audio_{job.uuid}.webm"
        with open(audio_path, "wb") as f:
            # f.write(await audio_file.read())
            shutil.copyfileobj(audio_file.file, f)

        await audio_file.close()
        del audio_file

        uploaded_audio = await AutomatedRecordService.upload_audio_file(
            db=db, job_uuid=job.uuid, audio_path=audio_path
        )

        transcribe_audio.apply_async(
            kwargs={"job_uuid": job.uuid, "file_name": uploaded_audio.name},
            countdown=30,
        )

        record = await TreatmentRecordService.update_treatment_record(
            db,
            record.uuid,
            user_uuid,
            TreatmentRecordUpdate(content="Reprocessando o áudio, aguarde..."),
        )

        return record


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
