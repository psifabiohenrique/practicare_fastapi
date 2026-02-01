from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ValidationError
from src.core.phone_utils import validate_and_normalize_phone
from src.models import Patient
from src.schemas import PatientCreate, PatientUpdate


class PatientService:
    @staticmethod
    async def get_patient(
        db: AsyncSession, patient_uuid: UUID
    ) -> Patient | None:
        result = await db.execute(
            select(Patient).filter(Patient.uuid == patient_uuid)
        )
        return result.scalars().first()

    @staticmethod
    async def get_patients(
        db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> list[Patient]:
        result = await db.execute(select(Patient).offset(skip).limit(limit))
        return list(result.scalars().all())

    @staticmethod
    async def create_patient(
        db: AsyncSession, patient_in: PatientCreate
    ) -> Patient:
        db_patient = PatientService._create_patient_model(patient_in)
        db.add(db_patient)
        await db.commit()
        await db.refresh(db_patient)
        return db_patient

    @staticmethod
    def _create_patient_model(patient_in: PatientCreate) -> Patient:
        data = patient_in.model_dump()
        data['first_name'] = data['first_name'].strip().title()
        data['last_name'] = data['last_name'].strip().title()
        if data.get("phone"):
            try:
                data["phone"] = validate_and_normalize_phone(data["phone"])
            except ValueError as e:
                raise ValidationError(str(e)) from e
        return Patient(**data)

    @staticmethod
    async def update_patient(
        db: AsyncSession, db_patient: Patient, patient_in: PatientUpdate
    ) -> Patient:
        PatientService._apply_update(db_patient, patient_in)
        db.add(db_patient)
        await db.commit()
        await db.refresh(db_patient)
        return db_patient

    @staticmethod
    def _apply_update(db_patient: Patient, patient_in: PatientUpdate) -> None:
        update_data = patient_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "phone" and value:
                try:
                    normalized_phone = validate_and_normalize_phone(value)
                    setattr(db_patient, field, normalized_phone)
                except ValueError as e:
                    raise ValidationError(str(e)) from e
            else:
                setattr(db_patient, field, value)

    @staticmethod
    async def delete_patient(
        db: AsyncSession, patient_uuid: UUID
    ) -> Patient | None:
        result = await db.execute(
            select(Patient).filter(Patient.uuid == patient_uuid)
        )
        db_patient = result.scalars().first()
        if db_patient:
            await db.delete(db_patient)
            await db.commit()
        return db_patient
