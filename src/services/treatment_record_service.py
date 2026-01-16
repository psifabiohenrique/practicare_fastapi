from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import ForbiddenError, NotFoundError
from src.models import TreatmentRecord
from src.schemas.treatment_record_schema import (
    TreatmentRecordCreate,
    TreatmentRecordUpdate,
)
from src.services.treatment_service import TreatmentService


class TreatmentRecordService:
    @staticmethod
    async def get_treatment_record(
        db: AsyncSession, treatment_record_uuid: UUID, user_uuid: str
    ) -> TreatmentRecord:
        result = await db.execute(
            select(TreatmentRecord)
            .options(selectinload(TreatmentRecord.treatment))
            .filter(TreatmentRecord.uuid == str(treatment_record_uuid))
        )

        record = result.scalars().first()
        if not record:
            raise NotFoundError("Treatment record not found")

        if record.treatment.user_uuid != user_uuid:
            raise ForbiddenError("Access denied to this treatment record")

        return record

    @staticmethod
    async def get_treatment_records(  # noqa: PLR0913, PLR0917
        db: AsyncSession,
        treatment_uuid: UUID,
        user_uuid: str,
        skip: int = 0,
        limit: int = 100,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[TreatmentRecord]:
        # Check if treatment exists and belongs to user
        await TreatmentService.get_treatment_by_uuid(
            db, treatment_uuid, user_uuid
        )
        query = select(TreatmentRecord).filter(
            TreatmentRecord.treatment_uuid == str(treatment_uuid)
        )
        if start_date:
            query = query.filter(TreatmentRecord.date >= start_date)
        if end_date:
            query = query.filter(TreatmentRecord.date <= end_date)

        query = (
            query
            .order_by(TreatmentRecord.record_number.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def create_treatment_record(
        db: AsyncSession, schema: TreatmentRecordCreate, user_uuid: str
    ) -> TreatmentRecord:
        # Check if treatment exists and belongs to user
        await TreatmentService.get_treatment_by_uuid(
            db, schema.treatment_uuid, user_uuid
        )

        # Generate record_number: max(record_number) + 1 for this treatment
        max_number_result = await db.execute(
            select(func.max(TreatmentRecord.record_number)).filter(
                TreatmentRecord.treatment_uuid == str(schema.treatment_uuid)
            )
        )
        current_max = max_number_result.scalar() or 0
        next_number = current_max + 1

        db_treatment_record = TreatmentRecord(
            **schema.model_dump(), record_number=next_number
        )
        db.add(db_treatment_record)
        await db.commit()
        await db.refresh(db_treatment_record)
        return db_treatment_record

    @staticmethod
    async def update_treatment_record(
        db: AsyncSession,
        treatment_record_uuid: UUID,
        user_uuid: str,
        schema: TreatmentRecordUpdate,
    ) -> TreatmentRecord:
        db_treatment_record = (
            await TreatmentRecordService.get_treatment_record(
                db, treatment_record_uuid, user_uuid
            )
        )

        update_data = schema.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_treatment_record, key, value)

        db.add(db_treatment_record)
        await db.commit()
        await db.refresh(db_treatment_record)
        return db_treatment_record
