from uuid import UUID

from sqlalchemy.orm import Session

from models import Patient
from schemas import PatientCreate, PatientUpdate
from utils.phone_utils import validate_and_normalize_phone


class PatientService:
    @staticmethod
    def get_patient(db: Session, patient_uuid: UUID) -> Patient | None:
        return db.query(Patient).filter(Patient.uuid == patient_uuid).first()

    @staticmethod
    def get_patients(
        db: Session, skip: int = 0, limit: int = 100
    ) -> list[Patient]:
        return db.query(Patient).offset(skip).limit(limit).all()

    @staticmethod
    def create_patient(db: Session, patient_in: PatientCreate) -> Patient:
        db_patient = PatientService._create_patient_model(patient_in)
        db.add(db_patient)
        db.commit()
        db.refresh(db_patient)
        return db_patient

    @staticmethod
    def _create_patient_model(patient_in: PatientCreate) -> Patient:
        data = patient_in.model_dump()
        if data.get("phone"):
            data["phone"] = validate_and_normalize_phone(data["phone"])
        return Patient(**data)

    @staticmethod
    def update_patient(
        db: Session, db_patient: Patient, patient_in: PatientUpdate
    ) -> Patient:
        PatientService._apply_update(db_patient, patient_in)
        db.add(db_patient)
        db.commit()
        db.refresh(db_patient)
        return db_patient

    @staticmethod
    def _apply_update(db_patient: Patient, patient_in: PatientUpdate) -> None:
        update_data = patient_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "phone" and value:
                normalized_phone = validate_and_normalize_phone(value)
                setattr(db_patient, field, normalized_phone)
            else:
                setattr(db_patient, field, value)

    @staticmethod
    def delete_patient(db: Session, patient_uuid: UUID) -> Patient | None:
        db_patient = (
            db.query(Patient).filter(Patient.uuid == patient_uuid).first()
        )
        if db_patient:
            db.delete(db_patient)
            db.commit()
        return db_patient
