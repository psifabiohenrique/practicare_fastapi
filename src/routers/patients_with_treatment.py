from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from models import User
from routers.deps import SessionDB, get_current_user
from schemas.patient_with_treatment import (
    PatientWithTreatmentCreate,
    PatientWithTreatmentUpdate,
    TreatmentWithPatientRead,
)
from services.patient_with_treatment_service import PatientWithTreatmentService
from utils.enums import Gender, Weekdays

router = APIRouter(
    prefix="/patients-with-treatment", tags=["Patients with Treatment"]
)


@router.post(
    "/",
    response_model=TreatmentWithPatientRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_patient_with_treatment(
    *,
    db: SessionDB,
    current_user: User = Depends(get_current_user),
    schema: PatientWithTreatmentCreate,
) -> any:
    """
    Create a new patient and their associated treatment.
    """
    try:
        (
            _,
            db_treatment,
        ) = await PatientWithTreatmentService.create_patient_with_treatment(
            db=db, schema=schema, user_uuid=current_user.uuid
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    return db_treatment


@router.get("/daily", response_model=list[TreatmentWithPatientRead])
async def get_daily_patients_with_treatment(
    *,
    db: SessionDB,
    current_user: User = Depends(get_current_user),
    weekday: Weekdays | None = Query(None),
) -> any:
    """
    Retrieve all treatments (with patient data) for the current user for
    today or a specific weekday. Ordered by start_time.
    """
    return await PatientWithTreatmentService.get_daily_treatments(
        db=db, user_uuid=current_user.uuid, weekday=weekday
    )


@router.get("/", response_model=list[TreatmentWithPatientRead])
async def get_patients_with_treatment(  # noqa: PLR0913
    *,
    db: SessionDB,
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    order_by: str | None = Query(None, pattern="^(name|birth_date)$"),
    order_dir: str = Query("asc", pattern="^(asc|desc)$"),
    gender: Gender | None = Query(None),
    weekday: Weekdays | None = Query(None),
    search: str | None = Query(None),
) -> any:
    """
    Retrieve all treatments (with patient data) for the current user.
    Supports pagination, filtering by gender/weekday,
    sorting by name/birth_date, and searching by name.
    """
    return await PatientWithTreatmentService.get_treatments_with_user_uuid(
        db=db,
        user_uuid=current_user.uuid,
        skip=skip,
        limit=limit,
        order_by=order_by,
        order_dir=order_dir,
        gender=gender,
        weekday=weekday,
        search=search,
    )


@router.get("/{treatment_uuid}", response_model=TreatmentWithPatientRead)
async def get_patient_with_treatment(
    *,
    db: SessionDB,
    current_user: User = Depends(get_current_user),
    treatment_uuid: UUID,
) -> any:
    """
    Get a specific treatment-patient record by treatment ID.
    Only allows access if the treatment belongs to the current user.
    """
    db_treatment = (
        await PatientWithTreatmentService.get_treatment_with_treatment_uuid(
            db=db, treatment_uuid=treatment_uuid
        )
    )
    if not db_treatment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Treatment not found",
        )
    if db_treatment.user_uuid != current_user.uuid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    return db_treatment


@router.patch("/{treatment_uuid}", response_model=TreatmentWithPatientRead)
async def update_patient_with_treatment(
    *,
    db: SessionDB,
    current_user: User = Depends(get_current_user),
    treatment_uuid: UUID,
    schema: PatientWithTreatmentUpdate,
) -> any:
    """
    Update both patient and treatment data.
    Only allows update if the treatment belongs to the current user.
    """
    # First check ownership
    db_treatment = (
        await PatientWithTreatmentService.get_treatment_with_treatment_uuid(
            db=db, treatment_uuid=treatment_uuid
        )
    )
    if not db_treatment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Treatment not found",
        )
    if db_treatment.user_uuid != current_user.uuid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Perform update
    try:
        (
            _,
            updated_treatment,
        ) = await PatientWithTreatmentService.update_patient_with_treatment(
            db=db,
            patient_uuid=db_treatment.patient_uuid,
            treatment_uuid=treatment_uuid,
            schema=schema,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    return updated_treatment
