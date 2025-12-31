from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from models import Patient, Treatment
from schemas.patient_with_treatment import (
    PatientWithTreatmentCreate,
    PatientWithTreatmentUpdate,
)
from services.patient_service import PatientService
from services.treatment_service import TreatmentService


class PatientWithTreatmentService:
    @staticmethod
    def get_patient_with_treatment_uuid(db: Session, treatment_uuid: UUID):
        """Returns the patient associated with a specific treatment ID,
        including treatment data."""
        return (
            db.query(Patient)
            .join(Treatment, Patient.uuid == Treatment.patient_uuid)
            .filter(Treatment.uuid == str(treatment_uuid))
            .options(joinedload(Patient.treatments))
            .first()
        )

    @staticmethod
    def get_patients_with_user_uuid(db: Session, user_uuid: str):
        """Returns all patients for a specific user,
        including their treatment data."""
        return (
            db.query(Patient)
            .join(Treatment, Patient.uuid == Treatment.patient_uuid)
            .filter(Treatment.user_uuid == user_uuid)
            .options(joinedload(Patient.treatments))
            .all()
        )

    @staticmethod
    def get_treatment_with_patient_uuid(db: Session, patient_uuid: str):
        """Returns the treatment for a specific patient UUID,
        including patient data."""
        return (
            db.query(Treatment)
            .filter(Treatment.patient_uuid == patient_uuid)
            .options(joinedload(Treatment.patient))
            .first()
        )

    @staticmethod
    def get_treatment_with_treatment_uuid(db: Session, treatment_uuid: UUID):
        """Returns a specific treatment by ID, including patient data."""
        return (
            db.query(Treatment)
            .filter(Treatment.uuid == str(treatment_uuid))
            .options(joinedload(Treatment.patient))
            .first()
        )

    @staticmethod
    def get_treatments_with_user_uuid(db: Session, user_uuid: str):
        """Returns all treatments for a specific user,
        including patient data."""
        return (
            db.query(Treatment)
            .filter(Treatment.user_uuid == user_uuid)
            .options(joinedload(Treatment.patient))
            .all()
        )

    @staticmethod
    def create_patient_with_treatment(
        db: Session, schema: PatientWithTreatmentCreate, user_uuid: str
    ):
        """Creates both a patient and a treatment in a single transaction."""
        # Reuse PatientService logic to create patient model
        db_patient = PatientService._create_patient_model(
            schema.patient_schema
        )
        db.add(db_patient)
        db.flush()  # Ensures uuid is generated if handled by db

        # Reuse TreatmentService logic to create treatment model
        db_treatment = TreatmentService._create_treatment_model(
            schema.treatment_schema
        )
        db_treatment.patient_uuid = db_patient.uuid
        db_treatment.user_uuid = user_uuid
        db.add(db_treatment)

        db.commit()
        db.refresh(db_patient)
        db.refresh(db_treatment)

        return db_patient, db_treatment

    @staticmethod
    def update_patient_with_treatment(
        db: Session,
        patient_uuid: str,
        treatment_uuid: UUID,
        schema: PatientWithTreatmentUpdate,
    ):
        """Updates both patient and treatment in a single transaction."""
        db_patient = (
            db.query(Patient).filter(Patient.uuid == str(patient_uuid)).first()
        )
        db_treatment = (
            db.query(Treatment)
            .filter(Treatment.uuid == str(treatment_uuid))
            .first()
        )

        if db_patient:
            PatientService._apply_update(db_patient, schema.patient_schema)
            db.add(db_patient)

        if db_treatment:
            TreatmentService._apply_update(
                db_treatment, schema.treatment_schema
            )
            db.add(db_treatment)

        db.commit()

        if db_patient:
            db.refresh(db_patient)
        if db_treatment:
            db.refresh(db_treatment)

        return db_patient, db_treatment
