from sqlalchemy.orm import Session

from models import Patient
from schemas import PatientCreate, PatientUpdate


class PatientService:
    @staticmethod
    def get_patient(db: Session, patient_id: int) -> Patient | None:
        return db.query(Patient).filter(Patient.id == patient_id).first()

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
        return Patient(**patient_in.model_dump())

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
            setattr(db_patient, field, value)

    @staticmethod
    def delete_patient(db: Session, patient_id: int) -> Patient | None:
        db_patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if db_patient:
            db.delete(db_patient)
            db.commit()
        return db_patient
