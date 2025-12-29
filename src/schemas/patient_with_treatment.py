from pydantic import BaseModel, ConfigDict

from schemas.patient import PatientCreate, PatientRead, PatientUpdate
from schemas.treatment import TreatmentCreate, TreatmentRead, TreatmentUpdate


class PatientWithTreatmentCreate(BaseModel):
    patient_schema: PatientCreate
    treatment_schema: TreatmentCreate


class PatientWithTreatmentUpdate(BaseModel):
    patient_schema: PatientUpdate
    treatment_schema: TreatmentUpdate


class PatientWithTreatmentRead(BaseModel):
    patient_schema: PatientRead
    treatment_schema: TreatmentRead

    model_config = ConfigDict(from_attributes=True)
