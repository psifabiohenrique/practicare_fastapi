import logging
from uuid import UUID

from fastapi import APIRouter, Query, status

from src.models import Gender, TreatmentStatus, Weekdays
from src.routers.deps import CurrentUser, SessionDB
from src.schemas.pagination_schema import PaginatedResponse
from src.schemas.patient_with_treatment_schema import (
    PatientWithTreatmentCreate,
    PatientWithTreatmentUpdate,
    TreatmentWithPatientRead,
)
from src.services.patient_with_treatment_service import (
    PatientWithTreatmentService,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/patients-with-treatment", tags=["Patients with Treatment"]
)


@router.post(
    "",
    response_model=TreatmentWithPatientRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_patient_with_treatment(
    *,
    db: SessionDB,
    current_user: CurrentUser,
    schema: PatientWithTreatmentCreate,
) -> any:
    """
    Create a new patient and their associated treatment.
    """
    logger.info(
        f"Criando novo paciente e tratamento. Usuário: {current_user.uuid}",
        extra={
            "user_uuid": str(current_user.uuid),
            "patient_name": schema.patient_schema.first_name,
        },
    )
    (
        _,
        db_treatment,
    ) = await PatientWithTreatmentService.create_patient_with_treatment(
        db=db, schema=schema, user_uuid=current_user.uuid
    )
    return db_treatment


@router.get("/daily", response_model=list[TreatmentWithPatientRead])
async def get_daily_patients_with_treatment(
    *,
    db: SessionDB,
    current_user: CurrentUser,
    weekday: Weekdays | None = Query(None),
) -> any:
    """
    Retrieve all treatments (with patient data) for the current user for
    today or a specific weekday. Ordered by start_time.
    """
    return await PatientWithTreatmentService.get_daily_treatments(
        db=db, user_uuid=current_user.uuid, weekday=weekday
    )


@router.get("", response_model=PaginatedResponse[TreatmentWithPatientRead])
async def get_patients_with_treatment(  # noqa: PLR0913
    *,
    db: SessionDB,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    order_by: str | None = Query(None, pattern="^(name|birth_date)$"),
    order_dir: str = Query("asc", pattern="^(asc|desc)$"),
    gender: Gender | None = Query(None),
    weekday: Weekdays | None = Query(None),
    status: TreatmentStatus | None = Query(None),
    search: str | None = Query(None),
) -> any:
    """
    Retrieve all treatments (with patient data) for the current user.
    Supports pagination, filtering by gender/weekday,
    sorting by name/birth_date, and searching by name.
    """
    (
        items,
        total,
    ) = await PatientWithTreatmentService.get_treatments_with_user_uuid(
        db=db,
        user_uuid=current_user.uuid,
        skip=skip,
        limit=limit,
        order_by=order_by,
        order_dir=order_dir,
        gender=gender,
        weekday=weekday,
        status=status,
        search=search,
    )
    return PaginatedResponse.create(
        items=items, total=total, skip=skip, limit=limit
    )


@router.get("/{treatment_uuid}", response_model=TreatmentWithPatientRead)
async def get_patient_with_treatment(
    *,
    db: SessionDB,
    current_user: CurrentUser,
    treatment_uuid: UUID,
) -> any:
    """
    Get a specific treatment-patient record by treatment ID.
    Only allows access if the treatment belongs to the current user.
    """
    return await PatientWithTreatmentService.get_treatment_with_treatment_uuid(
        db=db, treatment_uuid=treatment_uuid, user_uuid=current_user.uuid
    )


@router.patch("/{treatment_uuid}", response_model=TreatmentWithPatientRead)
async def update_patient_with_treatment(
    *,
    db: SessionDB,
    current_user: CurrentUser,
    treatment_uuid: UUID,
    schema: PatientWithTreatmentUpdate,
) -> any:
    """
    Update both patient and treatment data.
    Only allows update if the treatment belongs to the current user.
    """
    logger.info(
        f"Atualizando paciente e tratamento: {treatment_uuid}",
        extra={
            "user_uuid": str(current_user.uuid),
            "treatment_uuid": str(treatment_uuid),
        },
    )
    updated_treatment = (
        await PatientWithTreatmentService.update_patient_with_treatment(
            db=db,
            treatment_uuid=treatment_uuid,
            user_uuid=current_user.uuid,
            schema=schema,
        )
    )
    return updated_treatment


@router.post("/{treatment_uuid}", response_model=TreatmentWithPatientRead)
async def delete_patient_with_treatment(
    *,
    db: SessionDB,
    current_user: CurrentUser,
    treatment_uuid: str,
) -> TreatmentWithPatientRead:
    """
    Delete a specific treatment for the current user.
    """
    logger.info(
        f"Alterando status/excluindo tratamento: {treatment_uuid}",
        extra={
            "user_uuid": str(current_user.uuid),
            "treatment_uuid": treatment_uuid,
        },
    )
    result = await PatientWithTreatmentService.change_treatment_status(
        db=db, user_uuid=current_user.uuid, treatment_uuid=treatment_uuid
    )
    return result
