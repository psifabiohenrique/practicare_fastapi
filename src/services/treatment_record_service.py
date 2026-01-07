from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import TreatmentRecord
from schemas.treatment_record_schema import (
    TreatmentRecordCreate,
    TreatmentRecordUpdate,
)


class TreatmentRecordService:
    @staticmethod
    async def get_treatment_record(
        db: AsyncSession, treatment_record_uuid: UUID
    ) -> TreatmentRecord | None:
        result = await db.execute(
            select(TreatmentRecord).filter(
                TreatmentRecord.uuid == treatment_record_uuid
            )
        )
        return result.scalars().first()

    @staticmethod
    async def get_treatments_records(
        db: AsyncSession, treatment_uuid: UUID, skip: int = 0, limit: int = 100
    ) -> list[TreatmentRecord]:
        result = await db.execute(
            select(TreatmentRecord)
            .filter(TreatmentRecord.treatment_uuid == treatment_uuid)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_treatment_record(
        db: AsyncSession, schema: TreatmentRecordCreate
    ) -> TreatmentRecord:
        db_treatment_record = TreatmentRecord(**schema.dict())
        db.add(db_treatment_record)
        await db.commit()
        await db.refresh(db_treatment_record)
        return db_treatment_record

    @staticmethod
    async def update_treatment_record(
        db: AsyncSession,
        treatment_record_uuid: UUID,
        schema: TreatmentRecordUpdate,
    ) -> TreatmentRecord:
        db_treatment_record = (
            await TreatmentRecordService.get_treatment_records(
                db, treatment_record_uuid
            )
        )
        if not db_treatment_record:
            raise HTTPException(
                status_code=404, detail="Treatment record not found"
            )
        for key, value in schema.dict().items():
            setattr(db_treatment_record, key, value)
        db.add(db_treatment_record)
        await db.commit()
        await db.refresh(db_treatment_record)
        return db_treatment_record
