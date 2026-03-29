import logging
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import ForbiddenError, NotFoundError
from src.models import TreatmentReport
from src.schemas.treatment_report_schema import (
    TreatmentReportCreate,
    TreatmentReportUpdate,
)
from src.services.treatment_service import TreatmentService

logger = logging.getLogger(__name__)


class TreatmentReportService:
    @staticmethod
    async def get_treatment_report(
        db: AsyncSession, treatment_report_uuid: UUID, user_uuid: str
    ) -> TreatmentReport:
        result = await db.execute(
            select(TreatmentReport)
            .options(selectinload(TreatmentReport.treatment))
            .filter(TreatmentReport.uuid == str(treatment_report_uuid))
        )

        report = result.scalars().first()
        if not report:
            logger.warning(
                f"Relatório não encontrado: {treatment_report_uuid}"
            )
            raise NotFoundError("Treatment report not found")

        if report.treatment.user_uuid != user_uuid:
            logger.warning(
                f"Acesso negado ao relatório {treatment_report_uuid} pelo usuário {user_uuid}"  # noqa: E501
            )
            raise ForbiddenError("Access denied to this treatment report")

        return report

    @staticmethod
    async def get_treatment_reports(  # noqa: PLR0913, PLR0917
        db: AsyncSession,
        treatment_uuid: UUID,
        user_uuid: str,
        skip: int = 0,
        limit: int = 100,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[TreatmentReport]:
        # Check if treatment exists and belongs to user
        await TreatmentService.get_treatment_by_uuid(
            db, treatment_uuid, user_uuid
        )

        query = select(TreatmentReport).filter(
            TreatmentReport.treatment_uuid == str(treatment_uuid)
        )
        if start_date:
            query = query.filter(TreatmentReport.issue_date >= start_date)
        if end_date:
            query = query.filter(TreatmentReport.issue_date <= end_date)

        query = (
            query
            .order_by(TreatmentReport.issue_date.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def create_treatment_report(
        db: AsyncSession, schema: TreatmentReportCreate, user_uuid: str
    ) -> TreatmentReport:
        # Check if treatment exists and belongs to user
        await TreatmentService.get_treatment_by_uuid(
            db, schema.treatment_uuid, user_uuid
        )

        logger.info(
            f"Criando novo relatório para o tratamento: {schema.treatment_uuid}"  # noqa: E501
        )
        db_treatment_report = TreatmentReport(**schema.model_dump())
        db.add(db_treatment_report)
        await db.commit()
        await db.refresh(db_treatment_report)
        logger.info(f"Relatório {db_treatment_report.uuid} criado com sucesso")
        return db_treatment_report

    @staticmethod
    async def update_treatment_report(
        db: AsyncSession,
        treatment_report_uuid: UUID,
        user_uuid: str,
        schema: TreatmentReportUpdate,
    ) -> TreatmentReport:
        db_treatment_report = (
            await TreatmentReportService.get_treatment_report(
                db, treatment_report_uuid, user_uuid
            )
        )

        logger.info(f"Atualizando relatório: {treatment_report_uuid}")
        update_data = schema.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_treatment_report, key, value)

        db.add(db_treatment_report)
        await db.commit()
        await db.refresh(db_treatment_report)
        return db_treatment_report
