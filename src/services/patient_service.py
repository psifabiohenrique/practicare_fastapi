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
        db_patient = Patient(**patient_in.model_dump())
        db.add(db_patient)
        db.commit()
        db.refresh(db_patient)
        return db_patient

    @staticmethod
    def update_patient(
        db: Session, db_patient: Patient, patient_in: PatientUpdate
    ) -> Patient:
        update_data = patient_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_patient, field, value)
        db.add(db_patient)
        db.commit()
        db.refresh(db_patient)
        return db_patient

    @staticmethod
    def delete_patient(db: Session, patient_id: int) -> Patient | None:
        db_patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if db_patient:
            db.delete(db_patient)
            db.commit()
        return db_patient
