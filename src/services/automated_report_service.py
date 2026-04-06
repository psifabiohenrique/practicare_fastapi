import logging
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.chains.report_generation import ReportGenerationChain
from src.core.exceptions import NotFoundError
from src.models import TreatmentReport
from src.models.automated_report_job import AutomatedReportJob, ReportJobStatus
from src.models.treatment_context_model import TreatmentContext
from src.models.treatment_record_model import TreatmentRecord
from src.models.treatment_report_model import ReportStatus, ReportType
from src.models.usage_statistic import ProcessType
from src.schemas.dashboard_schema import UsageStatisticCreate
from src.schemas.treatment_report_schema import InternalTreatmentReportUpdate
from src.services.patient_with_treatment_service import (
    PatientWithTreatmentService,
)
from src.services.treatment_record_service import TreatmentRecordService
from src.services.treatment_report_service import TreatmentReportService
from src.services.usage_statistic_service import UsageStatisticService

logger = logging.getLogger(__name__)

RECENT_PERIOD_DAYS = 30


class AutomatedReportService:
    @staticmethod
    async def create_job(
        db: AsyncSession,
        treatment_uuid: UUID,
        treatment_report_uuid: UUID,
        user_uuid: str,
    ):
        logger.info(
            "Criando novo job de relatório para o tratamento: %s",
            treatment_uuid,
            extra={
                "user_uuid": str(user_uuid),
                "treatment_uuid": str(treatment_uuid),
                "treatment_report_uuid": str(treatment_report_uuid),
            },
        )
        job = AutomatedReportJob(
            user_uuid=user_uuid,
            treatment_uuid=str(treatment_uuid),
            treatment_report_uuid=str(treatment_report_uuid),
            status=ReportJobStatus.PENDING,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job

    @staticmethod
    async def get_job(db: AsyncSession, job_uuid: UUID):
        job = await db.execute(
            select(AutomatedReportJob).filter(
                AutomatedReportJob.uuid == str(job_uuid)
            )
        )
        job = job.scalar_one_or_none()
        if not job:
            raise NotFoundError("Job not found")
        return job

    @staticmethod
    async def update_job_status(
        db: AsyncSession,
        job_uuid: UUID,
        status: ReportJobStatus,
        error_message: str | None = None,
    ):
        job = await AutomatedReportService.get_job(db, job_uuid)
        job.status = status
        if error_message:
            job.error_message = error_message
        await db.commit()
        await db.refresh(job)
        return job

    @staticmethod
    async def process_automated_report_job(
        db: AsyncSession,
        job_uuid: UUID,
    ):
        """
        Main background task for processing an automated report job.
        """
        logger.info(
            f"Iniciando processamento do job de relatório: {job_uuid}",
            extra={"job_uuid": str(job_uuid)},
        )
        job = await AutomatedReportService.get_job(db, job_uuid)
        try:
            await AutomatedReportService.update_job_status(
                db, job_uuid, ReportJobStatus.GENERATING_REPORT
            )

            await AutomatedReportService.generate_report_content(db, job)

            await AutomatedReportService.update_job_status(
                db,
                job_uuid,
                ReportJobStatus.COMPLETED,
            )
            logger.info(
                "Geração de relatório concluída com sucesso para o job: %s",
                job_uuid,
                extra={"job_uuid": str(job_uuid)},
            )

        except Exception as e:
            logger.error(
                f"Erro ao gerar relatório do job {job_uuid}: {e}",
                exc_info=True,
                extra={"job_uuid": str(job_uuid)},
            )
            await AutomatedReportService.update_job_status(
                db, job_uuid, ReportJobStatus.FAILED, error_message=str(e)
            )
            try:
                await TreatmentReportService.update_treatment_report(
                    db=db,
                    treatment_report_uuid=job.treatment_report_uuid,
                    user_uuid=job.user_uuid,
                    schema=InternalTreatmentReportUpdate(
                        status=ReportStatus.FAILED,
                        demand_description="Falha na geração automática.",
                        procedures="Falha na geração automática.",
                        analysis="Falha na geração automática.",
                        conclusion="Falha na geração automática.",
                    ),
                )
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _get_first_record_date(
        db: AsyncSession, treatment_uuid: str
    ) -> date:
        """Returns the date of the earliest treatment record."""
        stmt = (
            select(TreatmentRecord.date)
            .filter(TreatmentRecord.treatment_uuid == treatment_uuid)
            .order_by(TreatmentRecord.date.asc())
            .limit(1)
        )
        result = await db.execute(stmt)
        first_date = result.scalar_one_or_none()
        return first_date if first_date else date.today()

    @staticmethod
    async def _get_last_report_date(
        db: AsyncSession, treatment_uuid: str, exclude_report_uuid: str
    ) -> date:
        """Returns the issue_date of the most recent report (excluding
        the current one being generated)."""
        stmt = (
            select(TreatmentReport.issue_date)
            .filter(
                TreatmentReport.treatment_uuid == treatment_uuid,
                TreatmentReport.uuid != exclude_report_uuid,
            )
            .order_by(TreatmentReport.issue_date.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        last_date = result.scalar_one_or_none()
        return last_date if last_date else date.today() - timedelta(days=30)

    @staticmethod
    async def _get_treatment_context(
        db: AsyncSession, treatment_uuid: str
    ) -> TreatmentContext | None:
        """Returns the TreatmentContext for a given treatment, if any."""
        stmt = select(TreatmentContext).filter(
            TreatmentContext.treatment_uuid == treatment_uuid
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def _format_treatment_context(ctx: TreatmentContext | None) -> str | None:
        """Formats TreatmentContext fields into a readable string."""
        if not ctx:
            return None
        parts = []
        if ctx.clinical_history:
            parts.append(f"Histórico Clínico:\n{ctx.clinical_history}")
        if ctx.psychological_patterns:
            parts.append(
                f"Padrões Psicológicos:\n{ctx.psychological_patterns}"
            )
        if ctx.therapeutic_goals:
            parts.append(
                f"Objetivos Terapêuticos:\n{ctx.therapeutic_goals}"
            )
        if ctx.life_dynamics:
            parts.append(
                f"Dinâmicas de Vida:\n{ctx.life_dynamics}"
            )
        if ctx.medication_notes:
            parts.append(
                f"Notas de Medicação:\n{ctx.medication_notes}"
            )
        return "\n\n".join(parts) if parts else None

    # ------------------------------------------------------------------
    # Main generation logic
    # ------------------------------------------------------------------

    @staticmethod
    async def _resolve_date_range(  # noqa: PLR0911
        db: AsyncSession,
        job: "AutomatedReportJob",
        report_type: ReportType,
        today: date,
    ) -> tuple[date, date, bool]:
        """
        Returns (start_date, end_date, include_context) for the report.
        """
        if report_type == ReportType.COMPLETO:
            start = await AutomatedReportService._get_first_record_date(
                db, str(job.treatment_uuid)
            )
            return start, today, True

        current_report_row = await TreatmentReportService.get_treatment_report(
            db=db,
            treatment_report_uuid=job.treatment_report_uuid,
            user_uuid=job.user_uuid,
        )
        provided_start = current_report_row.start_date_period
        provided_end = current_report_row.end_date_period
        dates_are_placeholder = (
            provided_start == today and provided_end == today
        )

        if report_type == ReportType.PERIODICO:
            if dates_are_placeholder:
                start = (
                    await AutomatedReportService._get_last_report_date(
                        db,
                        str(job.treatment_uuid),
                        str(job.treatment_report_uuid),
                    )
                )
                end = today
            else:
                start, end = provided_start, provided_end
            days_since_end = (today - end).days
            return start, end, days_since_end <= RECENT_PERIOD_DAYS

        # FOCADO
        if dates_are_placeholder:
            start = await AutomatedReportService._get_first_record_date(
                db, str(job.treatment_uuid)
            )
            return start, today, True
        return provided_start, provided_end, True

    @staticmethod
    async def generate_report_content(  # noqa: PLR0914
        db: AsyncSession, job: AutomatedReportJob
    ) -> dict:
        logger.info(
            f"Coletando contexto para o relatório do job: {job.uuid}",
            extra={"job_uuid": str(job.uuid)},
        )

        # 1. Patient info
        treatment_patient = (
            await PatientWithTreatmentService.get_patient_with_treatment_uuid(
                db=db,
                treatment_uuid=job.treatment_uuid,
                user_uuid=job.user_uuid,
            )
        )
        patient_first_name = treatment_patient.first_name.split()[0]
        gender = treatment_patient.gender

        # 2. Fetch current report to know type, dates and system_prompt
        current_report = await TreatmentReportService.get_treatment_report(
            db=db,
            treatment_report_uuid=job.treatment_report_uuid,
            user_uuid=job.user_uuid,
        )
        today = date.today()

        # 3. Resolve date range and context inclusion flag
        start_date, end_date, include_context = (
            await AutomatedReportService._resolve_date_range(
                db, job, current_report.report_type, today
            )
        )

        # 4. Fetch records for the resolved period
        records = await TreatmentRecordService.get_treatment_records(
            db=db,
            treatment_uuid=job.treatment_uuid,
            user_uuid=job.user_uuid,
            start_date=start_date,
            end_date=end_date,
            limit=1000,
        )

        records_context = ""
        for i, rec in enumerate(records):
            records_context += (
                f"Sessão {i + 1} ({rec.date}):\n{rec.content}\n\n"
            )

        if not records_context:
            logger.warning(
                "Nenhum prontuário encontrado para o job: %s",
                job.uuid,
                extra={"job_uuid": str(job.uuid)},
            )
            records_context = (
                "Nenhum prontuário encontrado para este período."
            )

        # 5. Fetch TreatmentContext if applicable
        treatment_context_str: str | None = None
        if include_context:
            ctx = await AutomatedReportService._get_treatment_context(
                db, str(job.treatment_uuid)
            )
            treatment_context_str = (
                AutomatedReportService._format_treatment_context(ctx)
            )

        # 6. Call AI
        logger.info(
            f"Chamando IA para geração de relatório do job: {job.uuid}",
            extra={"job_uuid": str(job.uuid)},
        )
        chain = ReportGenerationChain()
        result = await chain.generate(
            patient_first_name=patient_first_name,
            gender=gender,
            records_context=records_context,
            treatment_context=treatment_context_str,
            custom_system_prompt=current_report.system_prompt,
        )

        report_data = result.content

        # Save usage statistic
        await UsageStatisticService.create_statistic(
            db,
            UsageStatisticCreate(
                user_uuid=str(job.user_uuid),
                job_uuid=str(job.uuid),
                process_type=ProcessType.REPORT_GENERATION,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
            ),
        )

        # 7. Update report with generated content and real dates
        await TreatmentReportService.update_treatment_report(
            db=db,
            treatment_report_uuid=job.treatment_report_uuid,
            user_uuid=job.user_uuid,
            schema=InternalTreatmentReportUpdate(
                demand_description=report_data.demand_description,
                procedures=report_data.procedures,
                analysis=report_data.analysis,
                conclusion=report_data.conclusion,
                start_date_period=start_date,
                end_date_period=end_date,
                status=ReportStatus.READY,
            ),
        )

        logger.info(
            "Relatório gerado e salvo para o job: %s. "
            "Tokens: In %s, Out %s",
            job.uuid,
            result.input_tokens,
            result.output_tokens,
            extra={"job_uuid": str(job.uuid)},
        )
        return report_data
