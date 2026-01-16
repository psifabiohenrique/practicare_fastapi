import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.chains.report_generation import ReportGenerationChain
from src.core.exceptions import NotFoundError
from src.models import TreatmentReport
from src.models.automated_report_job import AutomatedReportJob, ReportJobStatus
from src.models.treatment_report_model import ReportStatus
from src.schemas.treatment_report_schema import InternalTreatmentReportUpdate
from src.services.patient_with_treatment_service import (
    PatientWithTreatmentService,
)
from src.services.treatment_record_service import TreatmentRecordService
from src.services.treatment_report_service import TreatmentReportService


class AutomatedReportService:
    @staticmethod
    async def create_job(
        db: AsyncSession,
        treatment_uuid: UUID,
        treatment_report_uuid: UUID,
        user_uuid: str,
    ):
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

        job.status = status  # type: ignore
        job.error_message = error_message  # type: ignore
        await db.commit()
        await db.refresh(job)

        return job

    @staticmethod
    async def generate_report_content(
        db: AsyncSession, job: AutomatedReportJob
    ):
        # 1. Buscar informações do paciente
        treatment_patient = (
            await PatientWithTreatmentService.get_patient_with_treatment_uuid(
                db=db,
                treatment_uuid=UUID(job.treatment_uuid),  # type: ignore
                user_uuid=job.user_uuid,  # type: ignore
            )
        )

        patient_first_name = treatment_patient.first_name.split()[0]
        gender = treatment_patient.gender

        # 2. Buscar o relatório atual para pegar as datas do período
        current_report = await TreatmentReportService.get_treatment_report(
            db=db,
            treatment_report_uuid=UUID(job.treatment_report_uuid),  # type: ignore
            user_uuid=job.user_uuid,  # type: ignore
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
            treatment_uuid=UUID(job.treatment_uuid),  # type: ignore
            user_uuid=job.user_uuid,  # type: ignore
            start_date=current_report.start_date_period,
            end_date=current_report.end_date_period,
            limit=1000,  # Pegar todos
        )

        records_context = ""
        for i, rec in enumerate(records):
            records_context += (
                f"Sessão {i + 1} ({rec.date}):\n{rec.content}\n\n"
            )

        if not records_context:
            records_context = "Nenhum prontuário encontrado para este período."

        # 5. Chamar IA
        chain = ReportGenerationChain()
        try:
            report_data = await chain.generate(
                patient_first_name=patient_first_name,
                gender=gender,  # type: ignore
                previous_report_context=previous_report_context,
                records_context=records_context,
            )

            # 6. Atualizar o relatório
            await TreatmentReportService.update_treatment_report(
                db=db,
                treatment_report_uuid=UUID(job.treatment_report_uuid),  # type: ignore
                user_uuid=job.user_uuid,  # type: ignore
                schema=InternalTreatmentReportUpdate(
                    demand_description=report_data.get("demand_description"),
                    procedures=report_data.get("procedures"),
                    analysis=report_data.get("analysis"),
                    conclusion=report_data.get("conclusion"),
                    status=ReportStatus.READY,
                ),
            )

            # 7. Atualizar o job
            job.generated_report_json = json.dumps(report_data)
            await AutomatedReportService.update_job_status(
                db=db,
                job_uuid=UUID(job.uuid),  # type: ignore
                status=ReportJobStatus.COMPLETED,
            )

        except Exception as e:
            await AutomatedReportService.update_job_status(
                db=db,
                job_uuid=UUID(job.uuid),  # type: ignore
                status=ReportJobStatus.FAILED,
                error_message=str(e),
            )
            # Atualiza o status do relatório para FAILED também
            await TreatmentReportService.update_treatment_report(
                db=db,
                treatment_report_uuid=UUID(job.treatment_report_uuid),  # type: ignore
                user_uuid=job.user_uuid,  # type: ignore
                schema=InternalTreatmentReportUpdate(
                    status=ReportStatus.FAILED,
                    demand_description="Falha na geração automática.",
                    procedures="Falha na geração automática.",
                    analysis="Falha na geração automática.",
                    conclusion="Falha na geração automática.",
                ),
            )
            raise e
