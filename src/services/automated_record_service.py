from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.chains.record_generation import RecordGenerationChain
from src.ai.chains.transcription import TranscriptionChain
from src.core.exceptions import NotFoundError
from src.models.automated_record_job import AutomatedRecordJob, JobStatus
from src.services.patient_with_treatment_service import (
    PatientWithTreatmentService,
)
from src.services.treatment_report_service import TreatmentReportService


class AutomatedRecordService:
    @staticmethod
    async def create_job(
        db: AsyncSession,
        treatment_uuid: UUID,
        treatment_record_uuid: UUID,
        user_uuid: str,
    ):

        # 2. Criar job no banco (PENDING)
        job = AutomatedRecordJob(
            user_uuid=user_uuid,
            treatment_uuid=str(treatment_uuid),
            treatment_record_uuid=str(treatment_record_uuid),
            status=JobStatus.PENDING,
            audio_path="",
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)

        return job

    @staticmethod
    async def get_job(db: AsyncSession, job_uuid: UUID):
        job = await db.execute(
            select(AutomatedRecordJob).filter(
                AutomatedRecordJob.uuid == str(job_uuid)
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
        status: JobStatus,
        transcription: str | None = None,
        error_message: str | None = None,
    ):
        job = await AutomatedRecordService.get_job(db, job_uuid)

        job.status = status  # type: ignore
        job.error_message = error_message  # type: ignore
        job.transcription = transcription
        await db.commit()
        await db.refresh(job)

        return job

    @staticmethod
    async def generate_record(
        db: AsyncSession, transcription: str, job: AutomatedRecordJob
    ) -> str:
        report_list = await TreatmentReportService.get_treatment_reports(
            db=db,
            treatment_uuid=job.treatment_uuid,  # pyright: ignore[reportArgumentType]
            user_uuid=job.user_uuid,  # pyright: ignore[reportArgumentType]
        )
        last_report_context = "Nenhum relatório produzido ainda. Está é a sessão inicial ou uma das sessões iniciais."  # noqa: E501
        if report_list:
            last_report_context = report_list[0]

        treatment_patient = (
            await PatientWithTreatmentService.get_patient_with_treatment_uuid(
                db=db,
                treatment_uuid=job.treatment_uuid,  # pyright: ignore[reportArgumentType]
                user_uuid=job.user_uuid,  # pyright: ignore[reportArgumentType]
            )
        )

        record_chain = RecordGenerationChain()
        try:
            record_text = await record_chain.generate(
                transcription=transcription,
                gender=treatment_patient.gender,  # pyright: ignore[reportArgumentType]
                context=last_report_context,
            )
            return record_text
        except Exception as e:
            await AutomatedRecordService.update_job_status(
                db=db,
                job_uuid=job.uuid,  # pyright: ignore[reportArgumentType]
                status=JobStatus.FAILED,
            )
            raise e

    @staticmethod
    async def generate_transcription(
        db: AsyncSession, audio_id: str, job_uuid: UUID
    ):
        transcription_chain = TranscriptionChain()
        from src.services.audio_storage_service import AudioStorageService

        try:
            # 1. Fetch content from provider
            audio_content = await AudioStorageService.get_file_content(
                audio_id
            )

            # 2. Transcribe
            transcription = await transcription_chain.transcribe(
                audio_content=audio_content
            )

            # 3. Cleanup from provider (fire and forget or background)
            # OpenAI Files should be deleted after use to avoid costs and clutter
            import asyncio

            asyncio.create_task(AudioStorageService.delete_file(audio_id))

            return transcription
        except Exception as e:
            await AutomatedRecordService.update_job_status(
                db=db,
                job_uuid=job_uuid,
                status=JobStatus.FAILED,
            )
            raise e
