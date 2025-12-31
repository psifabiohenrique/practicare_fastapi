from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from models import Patient, Treatment
from schemas.patient_with_treatment import (
    PatientWithTreatmentCreate,
    PatientWithTreatmentUpdate,
)
from services.patient_service import PatientService
from services.treatment_service import TreatmentService
from utils.enums import Gender, Weekdays


class PatientWithTreatmentService:
    @staticmethod
    def get_patient_with_treatment_uuid(db: Session, treatment_uuid: UUID):
        """Returns the patient associated with a specific treatment ID,
        including treatment data."""
        return (
            db
            .query(Patient)
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
            db
            .query(Patient)
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
            db
            .query(Treatment)
            .filter(Treatment.patient_uuid == patient_uuid)
            .options(joinedload(Treatment.patient))
            .first()
        )

    @staticmethod
    def get_treatment_with_treatment_uuid(db: Session, treatment_uuid: UUID):
        """Returns a specific treatment by ID, including patient data."""
        return (
            db
            .query(Treatment)
            .filter(Treatment.uuid == str(treatment_uuid))
            .options(joinedload(Treatment.patient))
            .first()
        )

    @staticmethod
    def get_treatments_with_user_uuid(  # noqa: PLR0913, PLR0917
        db: Session,
        user_uuid: str,
        skip: int = 0,
        limit: int = 100,
        order_by: str | None = None,
        order_dir: str = "asc",
        gender: Gender | None = None,
        weekday: Weekdays | None = None,
        search: str | None = None,
    ):
        """Returns all treatments for a specific user, including patient data,
        with support for filtering, sorting and pagination."""
        query = (
            db
            .query(Treatment)
            .join(Patient, Treatment.patient_uuid == Patient.uuid)
            .filter(Treatment.user_uuid == user_uuid)
        )

        if gender:
            query = query.filter(Patient.gender == gender)
        if weekday:
            query = query.filter(Treatment.weekday == weekday)
        if search:
            query = query.filter(
                or_(
                    Patient.first_name.ilike(f"%{search}%"),
                    Patient.last_name.ilike(f"%{search}%"),
                )
            )

        if order_by == "name":
            col = Patient.first_name
            if order_dir == "desc":
                query = query.order_by(col.desc())
            else:
                query = query.order_by(col.asc())
        elif order_by == "birth_date":
            col = Patient.birth_date
            if order_dir == "desc":
                query = query.order_by(col.desc())
            else:
                query = query.order_by(col.asc())

        return (
            query
            .options(joinedload(Treatment.patient))
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_daily_treatments(
        db: Session,
        user_uuid: str,
        weekday: Weekdays | None = None,
    ):
        """Returns all treatments for a specific user on a given
        weekday (defaults to today), ordered by start_time."""
        if not weekday:
            from datetime import datetime  # noqa: PLC0415

            weekday_str = datetime.now().strftime("%A")
            weekday = Weekdays(weekday_str)

        return (
            db
            .query(Treatment)
            .filter(Treatment.user_uuid == user_uuid)
            .filter(Treatment.weekday == weekday)
            .options(joinedload(Treatment.patient))
            .order_by(Treatment.start_time.asc())
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
            db
            .query(Treatment)
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
