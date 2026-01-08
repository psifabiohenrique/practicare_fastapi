from uuid import UUID

from fastapi import APIRouter, status

from routers.deps import CurrentUser, SessionDB
from schemas.treatment_record_schema import (
    TreatmentRecordCreate,
    TreatmentRecordRead,
    TreatmentRecordUpdate,
)
from services.treatment_record_service import TreatmentRecordService

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
