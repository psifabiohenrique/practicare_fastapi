from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from models import User
from routers.deps import SessionDB, get_current_user
from schemas.patient_with_treatment import (
    PatientWithTreatmentCreate,
    PatientWithTreatmentUpdate,
    TreatmentWithPatientRead,
)
from services.patient_with_treatment_service import PatientWithTreatmentService

router = APIRouter(
    prefix="/patients-with-treatment", tags=["Patients with Treatment"]
)


@router.post(
    "/",
    response_model=TreatmentWithPatientRead,
    status_code=status.HTTP_201_CREATED,
)
def create_patient_with_treatment(
    *,
    db: SessionDB,
    current_user: User = Depends(get_current_user),
    schema: PatientWithTreatmentCreate,
) -> any:
    """
    Create a new patient and their associated treatment.
    """
    db_patient, db_treatment = (
        PatientWithTreatmentService.create_patient_with_treatment(
            db=db, schema=schema, user_uuid=current_user.uuid
        )
    )
    return db_treatment


@router.get("/", response_model=list[TreatmentWithPatientRead])
def get_patients_with_treatment(
    db: SessionDB,
    current_user: User = Depends(get_current_user),
) -> any:
    """
    Retrieve all treatments (with patient data) for the current user.
    """
    return PatientWithTreatmentService.get_treatments_with_user_uuid(
        db=db, user_uuid=current_user.uuid
    )


@router.get("/{treatment_uuid}", response_model=TreatmentWithPatientRead)
def get_patient_with_treatment(
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
        PatientWithTreatmentService.get_treatment_with_treatment_uuid(
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
def update_patient_with_treatment(
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
        PatientWithTreatmentService.get_treatment_with_treatment_uuid(
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
    _, updated_treatment = (
        PatientWithTreatmentService.update_patient_with_treatment(
            db=db,
            patient_uuid=db_treatment.patient_uuid,
            treatment_uuid=treatment_uuid,
            schema=schema,
        )
    )
    return updated_treatment
