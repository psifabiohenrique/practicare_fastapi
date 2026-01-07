from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Treatment
from schemas import TreatmentCreate, TreatmentUpdate


class TreatmentService:
    @staticmethod
    async def get_treatment(
        db: AsyncSession, treatment_id: int
    ) -> Treatment | None:
        result = await db.execute(
            select(Treatment).filter(Treatment.id == treatment_id)
        )
        return result.scalars().first()

    @staticmethod
    async def get_treatments(
        db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> list[Treatment]:
        result = await db.execute(select(Treatment).offset(skip).limit(limit))
        return list(result.scalars().all())

    @staticmethod
    async def create_treatment(
        db: AsyncSession, treatment_in: TreatmentCreate
    ) -> Treatment:
        db_treatment = TreatmentService._create_treatment_model(treatment_in)
        db.add(db_treatment)
        await db.commit()
        await db.refresh(db_treatment)
        return db_treatment

    @staticmethod
    def _create_treatment_model(treatment_in: TreatmentCreate) -> Treatment:
        return Treatment(**treatment_in.model_dump())

    @staticmethod
    async def update_treatment(
        db: AsyncSession,
        db_treatment: Treatment,
        treatment_in: TreatmentUpdate,
    ) -> Treatment:
        TreatmentService._apply_update(db_treatment, treatment_in)
        db.add(db_treatment)
        await db.commit()
        await db.refresh(db_treatment)
        return db_treatment

    @staticmethod
    def _apply_update(
        db_treatment: Treatment, treatment_in: TreatmentUpdate
    ) -> None:
        update_data = treatment_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_treatment, field, value)

    @staticmethod
    async def delete_treatment(
        db: AsyncSession, treatment_id: int
    ) -> Treatment | None:
        result = await db.execute(
            select(Treatment).filter(Treatment.id == treatment_id)
        )
        db_treatment = result.scalars().first()
        if db_treatment:
            await db.delete(db_treatment)
            await db.commit()
        return db_treatment
