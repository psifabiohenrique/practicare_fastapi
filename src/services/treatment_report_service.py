from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.exceptions import ForbiddenError, NotFoundError
from models import TreatmentReport
from schemas.treatment_report_schema import (
    TreatmentReportCreate,
    TreatmentReportUpdate,
)
from services.treatment_service import TreatmentService


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
            raise NotFoundError("Treatment report not found")

        if report.treatment.user_uuid != user_uuid:
            raise ForbiddenError("Access denied to this treatment report")

        return report

    @staticmethod
    async def get_treatment_reports(
        db: AsyncSession,
        treatment_uuid: UUID,
        user_uuid: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[TreatmentReport]:
        # Check if treatment exists and belongs to user
        await TreatmentService.get_treatment_by_uuid(
            db, treatment_uuid, user_uuid
        )

        result = await db.execute(
            select(TreatmentReport)
            .filter(TreatmentReport.treatment_uuid == str(treatment_uuid))
            .order_by(TreatmentReport.issue_date.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_treatment_report(
        db: AsyncSession, schema: TreatmentReportCreate, user_uuid: str
    ) -> TreatmentReport:
        # Check if treatment exists and belongs to user
        await TreatmentService.get_treatment_by_uuid(
            db, schema.treatment_uuid, user_uuid
        )

        db_treatment_report = TreatmentReport(**schema.model_dump())
        db.add(db_treatment_report)
        await db.commit()
        await db.refresh(db_treatment_report)
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

        update_data = schema.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_treatment_report, key, value)

        db.add(db_treatment_report)
        await db.commit()
        await db.refresh(db_treatment_report)
        return db_treatment_report
