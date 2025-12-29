from typing import Any

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
) -> Any:
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
) -> Any:
    """
    Retrieve all treatments (with patient data) for the current user.
    """
    return PatientWithTreatmentService.get_treatments_with_user_uuid(
        db=db, user_uuid=current_user.uuid
    )


@router.get("/{treatment_id}", response_model=TreatmentWithPatientRead)
def get_patient_with_treatment(
    *,
    db: SessionDB,
    current_user: User = Depends(get_current_user),
    treatment_id: int,
) -> Any:
    """
    Get a specific treatment-patient record by treatment ID.
    Only allows access if the treatment belongs to the current user.
    """
    db_treatment = PatientWithTreatmentService.get_treatment_with_treatment_id(
        db=db, treatment_id=treatment_id
    )
    if not db_treatment or db_treatment.user_uuid != current_user.uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Treatment not found or access denied",
        )
    return db_treatment


@router.patch("/{treatment_id}", response_model=TreatmentWithPatientRead)
def update_patient_with_treatment(
    *,
    db: SessionDB,
    current_user: User = Depends(get_current_user),
    treatment_id: int,
    schema: PatientWithTreatmentUpdate,
) -> Any:
    """
    Update both patient and treatment data.
    Only allows update if the treatment belongs to the current user.
    """
    # First check ownership
    db_treatment = PatientWithTreatmentService.get_treatment_with_treatment_id(
        db=db, treatment_id=treatment_id
    )
    if not db_treatment or db_treatment.user_uuid != current_user.uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Treatment not found or access denied",
        )

    # Perform update
    _, updated_treatment = (
        PatientWithTreatmentService.update_patient_with_treatment(
            db=db,
            patient_uuid=db_treatment.patient_id,
            treatment_id=treatment_id,
            schema=schema,
        )
    )
    return updated_treatment
