from uuid import UUID

from fastapi import APIRouter, status

from src.routers.deps import CurrentUser, SessionDB
from src.schemas.treatment_report_schema import (
    TreatmentReportCreate,
    TreatmentReportRead,
    TreatmentReportUpdate,
)
from src.services.treatment_report_service import TreatmentReportService

router = APIRouter(prefix="/treatment-reports", tags=["Treatment reports"])


@router.get(
    "/treatment/{treatment_uuid}", response_model=list[TreatmentReportRead]
)
async def list_treatment_reports(
    treatment_uuid: UUID,
    db: SessionDB,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> any:
    return await TreatmentReportService.get_treatment_reports(
        db, treatment_uuid, current_user.uuid, skip, limit
    )


@router.get("/{treatment_report_uuid}", response_model=TreatmentReportRead)
async def get_treatment_report(
    treatment_report_uuid: UUID,
    db: SessionDB,
    current_user: CurrentUser,
) -> any:
    return await TreatmentReportService.get_treatment_report(
        db, treatment_report_uuid, current_user.uuid
    )


@router.post(
    "/",
    response_model=TreatmentReportRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_treatment_report(
    schema: TreatmentReportCreate,
    db: SessionDB,
    current_user: CurrentUser,
) -> any:
    return await TreatmentReportService.create_treatment_report(
        db, schema, current_user.uuid
    )


@router.patch("/{treatment_report_uuid}", response_model=TreatmentReportRead)
async def update_treatment_report(
    treatment_report_uuid: UUID,
    schema: TreatmentReportUpdate,
    db: SessionDB,
    current_user: CurrentUser,
) -> any:
    return await TreatmentReportService.update_treatment_report(
        db, treatment_report_uuid, current_user.uuid, schema
    )
