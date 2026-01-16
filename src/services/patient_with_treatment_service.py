from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from src.core.exceptions import ForbiddenError, NotFoundError
from src.models import Gender, Patient, Treatment, Weekdays
from src.schemas.patient_with_treatment_schema import (
    PatientWithTreatmentCreate,
    PatientWithTreatmentUpdate,
)
from src.services.patient_service import PatientService
from src.services.treatment_service import TreatmentService


class PatientWithTreatmentService:
    @staticmethod
    async def get_patient_with_treatment_uuid(
        db: AsyncSession, treatment_uuid: UUID, user_uuid: str
    ):
        """Returns the patient associated with a specific treatment ID,
        including treatment data."""
        result = await db.execute(
            select(Patient)
            .join(Treatment, Patient.uuid == Treatment.patient_uuid)
            .filter(Treatment.uuid == str(treatment_uuid))
            .options(joinedload(Patient.treatments))
        )
        patient = result.scalars().first()
        if not patient:
            raise NotFoundError("Patient or Treatment not found")

        # Treatment ownership check (checking first treatment
        # found for simplicity, but the query ensures it matches
        # treatment_uuid)
        treatment = next(
            (t for t in patient.treatments if t.uuid == str(treatment_uuid)),
            None,
        )
        if treatment and treatment.user_uuid != user_uuid:
            raise ForbiddenError("Access denied")

        return patient

    @staticmethod
    async def get_patients_with_user_uuid(db: AsyncSession, user_uuid: str):
        """Returns all patients for a specific user,
        including their treatment data."""
        result = await db.execute(
            select(Patient)
            .join(Treatment, Patient.uuid == Treatment.patient_uuid)
            .filter(Treatment.user_uuid == user_uuid)
            .options(joinedload(Patient.treatments))
        )
        return list(result.scalars().unique().all())

    @staticmethod
    async def get_treatment_with_patient_uuid(
        db: AsyncSession, patient_uuid: str
    ):
        """Returns the treatment for a specific patient UUID,
        including patient data."""
        result = await db.execute(
            select(Treatment)
            .filter(Treatment.patient_uuid == patient_uuid)
            .options(joinedload(Treatment.patient))
        )
        return result.scalars().first()

    @staticmethod
    async def get_treatment_with_treatment_uuid(
        db: AsyncSession, treatment_uuid: UUID, user_uuid: str
    ):
        """Returns a specific treatment by ID, including patient data."""
        result = await db.execute(
            select(Treatment)
            .filter(Treatment.uuid == str(treatment_uuid))
            .options(joinedload(Treatment.patient))
        )
        treatment = result.scalars().first()
        if not treatment:
            raise NotFoundError("Treatment not found")
        if treatment.user_uuid != user_uuid:
            raise ForbiddenError("Access denied")
        return treatment

    @staticmethod
    async def get_treatments_with_user_uuid(  # noqa: PLR0913, PLR0917
        db: AsyncSession,
        user_uuid: str,
        skip: int = 0,
        limit: int = 100,
        order_by: str | None = None,
        order_dir: str = "asc",
        gender: Gender | None = None,
        weekday: Weekdays | None = None,
        search: str | None = None,
    ):
        """Returns all treatments for a specific user,
        including patient data, with support for filtering,
        sorting and pagination."""
        query = (
            select(Treatment)
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

        result = await db.execute(
            query
            .options(joinedload(Treatment.patient))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_daily_treatments(
        db: AsyncSession,
        user_uuid: str,
        weekday: Weekdays | None = None,
    ):
        """Returns all treatments for a specific user on a given
        weekday (defaults to today), ordered by start_time."""
        if not weekday:
            weekday_str = datetime.now().strftime("%A")
            weekday = Weekdays(weekday_str)

        result = await db.execute(
            select(Treatment)
            .filter(Treatment.user_uuid == user_uuid)
            .filter(Treatment.weekday == weekday)
            .options(joinedload(Treatment.patient))
            .order_by(Treatment.start_time.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_patient_with_treatment(
        db: AsyncSession, schema: PatientWithTreatmentCreate, user_uuid: str
    ):
        """Creates both a patient and a treatment in a single transaction."""
        # Reuse PatientService logic to create patient model
        db_patient = PatientService._create_patient_model(
            schema.patient_schema
        )
        db.add(db_patient)
        await db.flush()

        # Reuse TreatmentService logic to create treatment model
        db_treatment = TreatmentService._create_treatment_model(
            schema.treatment_schema
        )
        db_treatment.patient_uuid = db_patient.uuid
        db_treatment.user_uuid = user_uuid
        db.add(db_treatment)

        await db.commit()
        await db.refresh(db_patient)
        await db.refresh(db_treatment, ["patient"])

        return db_patient, db_treatment

    @staticmethod
    async def update_patient_with_treatment(
        db: AsyncSession,
        treatment_uuid: UUID,
        user_uuid: str,
        schema: PatientWithTreatmentUpdate,
    ):
        """Updates both patient and treatment in a single transaction."""
        db_treatment = await PatientWithTreatmentService.get_treatment_with_treatment_uuid(  # noqa: E501
            db, treatment_uuid, user_uuid
        )

        treatment_uuid_value = db_treatment.uuid
        patient_uuid_value = db_treatment.patient_uuid

        # Get the associated patient
        res_patient = await db.execute(
            select(Patient).filter(Patient.uuid == patient_uuid_value)
        )
        db_patient = res_patient.scalars().first()
        if not db_patient:
            raise NotFoundError("Associated patient not found")

        PatientService._apply_update(db_patient, schema.patient_schema)
        TreatmentService._apply_update(db_treatment, schema.treatment_schema)

        await db.commit()

        stmt = (
            select(Treatment)
            .where(Treatment.uuid == treatment_uuid_value)
            .options(
                selectinload(Treatment.patient),
                selectinload(Treatment.user),
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one()
