import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ForbiddenError, NotFoundError
from src.models import Treatment
from src.schemas import (
    TreatmentCreate,
    TreatmentUpdate,
    TreatmentUpdateInternal,
)

logger = logging.getLogger(__name__)


class TreatmentService:
    @staticmethod
    async def get_treatment_by_uuid(
        db: AsyncSession, treatment_uuid: UUID, user_uuid: str
    ) -> Treatment:
        result = await db.execute(
            select(Treatment).filter(Treatment.uuid == str(treatment_uuid))
        )
        treatment = result.scalars().first()
        if not treatment:
            logger.warning(f"Tratamento não encontrado: {treatment_uuid}")
            raise NotFoundError("Treatment not found")
        if str(treatment.user_uuid) != str(user_uuid):
            logger.warning(
                f"Tentativa de acesso negado ao tratamento {treatment_uuid} pelo usuário {user_uuid}"  # noqa: E501
            )
            raise ForbiddenError("Access denied to this treatment")

        return treatment

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
        logger.info("Criando novo tratamento")
        db_treatment = TreatmentService._create_treatment_model(treatment_in)
        db.add(db_treatment)
        await db.commit()
        await db.refresh(db_treatment)
        logger.info(f"Tratamento criado com sucesso: {db_treatment.uuid}")
        return db_treatment

    @staticmethod
    def _create_treatment_model(treatment_in: TreatmentCreate) -> Treatment:
        return Treatment(**treatment_in.model_dump())

    @staticmethod
    async def update_treatment(
        db: AsyncSession,
        db_treatment: Treatment,
        treatment_in: TreatmentUpdate | TreatmentUpdateInternal,
    ) -> Treatment:
        logger.info(f"Atualizando tratamento: {db_treatment.uuid}")
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
        db: AsyncSession, treatment_uuid: UUID
    ) -> Treatment | None:
        logger.info(f"Excluindo tratamento: {treatment_uuid}")
        result = await db.execute(
            select(Treatment).filter(Treatment.uuid == str(treatment_uuid))
        )
        db_treatment = result.scalars().first()
        if db_treatment:
            await db.delete(db_treatment)
            await db.commit()
            logger.info(f"Tratamento {treatment_uuid} excluído com sucesso")
        else:
            logger.warning(
                f"Tentativa de excluir tratamento inexistente: {treatment_uuid}"  # noqa: E501
            )
        return db_treatment
