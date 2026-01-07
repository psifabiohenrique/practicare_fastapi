from pydantic import BaseModel, ConfigDict

from schemas.patient_schema import PatientCreate, PatientRead, PatientUpdate
from schemas.treatment_schema import (
    TreatmentCreate,
    TreatmentRead,
    TreatmentUpdate,
)


class PatientWithTreatmentCreate(BaseModel):
    patient_schema: PatientCreate
    treatment_schema: TreatmentCreate


class PatientWithTreatmentUpdate(BaseModel):
    patient_schema: PatientUpdate
    treatment_schema: TreatmentUpdate


class PatientWithTreatmentRead(BaseModel):
    patient: PatientRead
    treatment: TreatmentRead

    model_config = ConfigDict(from_attributes=True)


class TreatmentWithPatientRead(TreatmentRead):
    patient: PatientRead

    model_config = ConfigDict(from_attributes=True)
