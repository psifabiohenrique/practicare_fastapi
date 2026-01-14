from datetime import date
from http import HTTPStatus
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

from routers.deps import CurrentUser, SessionDB
from schemas.treatment_record_schema import (
    TreatmentRecordCreate,
    TreatmentRecordRead,
    TreatmentRecordUpdate,
)
from services.automated_record_service import AutomatedRecordService
from services.treatment_record_service import TreatmentRecordService
from services.treatment_service import TreatmentService
from tasks.record_generation import transcribe_audio

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
    "/",
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
async def upload_audio(
    treatment_uuid: UUID,
    db: SessionDB,
    current_user: CurrentUser,
    session_date: Annotated[date, Body()],
    audio_file: UploadFile = File(...),
):

    user_uuid = current_user.uuid
    if audio_file.content_type not in {
        "audio/webm",
        "video/webm",
        "audio/ogg",
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
            status="pending",
            date=session_date,
            start_time=treatment.start_time,
            end_time=treatment.end_time,
            content="Processing",
        ),
        user_uuid=user_uuid,
    )

    job = await AutomatedRecordService.create_job(
        db=db,
        treatment_uuid=treatment_uuid,
        user_uuid=user_uuid,
        treatment_record_uuid=record.uuid,
    )

    audio_bytes = await audio_file.read()

    transcribe_audio.delay(job_uuid=job.uuid, audio=audio_bytes)
    # transcribe_audio.delay(job_uuid=job.uuid)

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
