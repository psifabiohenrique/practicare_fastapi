import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.chains.report_generation import ReportGenerationChain
from src.core.exceptions import NotFoundError
from src.models import TreatmentReport
from src.models.automated_report_job import AutomatedReportJob, ReportJobStatus
from src.models.treatment_report_model import ReportStatus
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
        db: AsyncSession,  # AsyncSession factory
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
            # 1. Update status to GENERATING_REPORT
            await AutomatedReportService.update_job_status(
                db, job_uuid, ReportJobStatus.GENERATING_REPORT
            )

            # 2. Gather context and generate report
            await AutomatedReportService.generate_report_content(db, job)

            # 3. Complete job
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
            # Update report status to FAILED
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

    @staticmethod
    async def generate_report_content(
        db: AsyncSession, job: AutomatedReportJob
    ) -> dict:
        logger.info(
            f"Coletando contexto para o relatório do job: {job.uuid}",
            extra={"job_uuid": str(job.uuid)},
        )
        # 1. Buscar informações do paciente
        treatment_patient = (
            await PatientWithTreatmentService.get_patient_with_treatment_uuid(
                db=db,
                treatment_uuid=job.treatment_uuid,
                user_uuid=job.user_uuid,
            )
        )

        patient_first_name = treatment_patient.first_name.split()[0]
        gender = treatment_patient.gender

        # 2. Buscar o relatório atual para pegar as datas do período
        current_report = await TreatmentReportService.get_treatment_report(
            db=db,
            treatment_report_uuid=job.treatment_report_uuid,
            user_uuid=job.user_uuid,
        )

        # 3. Buscar o relatório mais recente anterior ao período
        stmt = (
            select(TreatmentReport)
            .filter(
                TreatmentReport.treatment_uuid == job.treatment_uuid,
                TreatmentReport.end_date_period
                < current_report.start_date_period,
            )
            .order_by(TreatmentReport.end_date_period.desc())
            .limit(1)
        )
        prev_report_res = await db.execute(stmt)
        previous_report = prev_report_res.scalar_one_or_none()

        previous_report_context = "Nenhum relatório anterior encontrado."
        if previous_report:
            previous_report_context = (
                f"Demanda: {previous_report.demand_description}\n"
                f"Procedimentos: {previous_report.procedures}\n"
                f"Análise: {previous_report.analysis}\n"
                f"Conclusão: {previous_report.conclusion}"
            )

        # 4. Buscar prontuários do período
        records = await TreatmentRecordService.get_treatment_records(
            db=db,
            treatment_uuid=job.treatment_uuid,
            user_uuid=job.user_uuid,
            start_date=current_report.start_date_period,
            end_date=current_report.end_date_period,
            limit=1000,
        )

        records_context = ""
        for i, rec in enumerate(records):
            records_context += (
                f"Sessão {i + 1} ({rec.date}):\n{rec.content}\n\n"
            )

        if not records_context:
            logger.warning(
                "Nenhum prontuário encontrado para o período no job: %s",
                job.uuid,
                extra={"job_uuid": str(job.uuid)},
            )
            records_context = "Nenhum prontuário encontrado para este período."

        # 5. Chamar IA
        logger.info(
            f"Chamando IA para geração de relatório do job: {job.uuid}",
            extra={"job_uuid": str(job.uuid)},
        )
        chain = ReportGenerationChain()
        result = await chain.generate(
            patient_first_name=patient_first_name,
            gender=gender,
            previous_report_context=previous_report_context,
            records_context=records_context,
        )

        report_data = result.content

        # Save report generation usage statistic
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

        # 6. Atualizar o relatório
        await TreatmentReportService.update_treatment_report(
            db=db,
            treatment_report_uuid=job.treatment_report_uuid,
            user_uuid=job.user_uuid,
            schema=InternalTreatmentReportUpdate(
                demand_description=report_data.demand_description,
                procedures=report_data.procedures,
                analysis=report_data.analysis,
                conclusion=report_data.conclusion,
                status=ReportStatus.READY,
            ),
        )

        logger.info(
            "Relatório gerado e salvo para o job: %s. Tokens: In %s, Out %s",
            job.uuid,
            result.input_tokens,
            result.output_tokens,
            extra={"job_uuid": str(job.uuid)},
        )
        return report_data
