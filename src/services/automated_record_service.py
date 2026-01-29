import logging
import os
import shutil
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.chains.record_generation import RecordGenerationChain
from src.ai.chains.transcription import TranscriptionChain
from src.core.exceptions import NotFoundError
from src.models.automated_record_job import AutomatedRecordJob, JobStatus
from src.models.treatment_record_model import RecordStatus
from src.schemas.treatment_record_schema import (
    InternalTreatmentRecordUpdate,
)
from src.services.patient_with_treatment_service import (
    PatientWithTreatmentService,
)
from src.services.treatment_record_service import (
    TreatmentRecordService,
)
from src.services.treatment_report_service import TreatmentReportService
from src.utils.audio_processor import convert_to_wav, split_by_vad

logger = logging.getLogger(__name__)


class AutomatedRecordService:
    @staticmethod
    async def create_job(
        db: AsyncSession,
        treatment_uuid: UUID,
        treatment_record_uuid: UUID,
        user_uuid: str,
        audio_path: str = "",
    ):
        job = AutomatedRecordJob(
            user_uuid=user_uuid,
            treatment_uuid=str(treatment_uuid),
            treatment_record_uuid=str(treatment_record_uuid),
            status=JobStatus.PENDING,
            audio_path=audio_path,
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
        audio_path: str | None = None,
    ):
        job = await AutomatedRecordService.get_job(db, job_uuid)
        job.status = status
        if error_message:
            job.error_message = error_message
        if transcription:
            job.transcription = transcription
        if audio_path:
            job.audio_path = audio_path
        await db.commit()
        await db.refresh(job)
        return job

    @staticmethod
    async def upload_audio_file(
        db: AsyncSession,  # AsyncSession factory or session
        job_uuid: UUID,
        audio_path: str,
    ):
        """
        Main background task for processing an automated record job.
        """
        job = await AutomatedRecordService.get_job(db, job_uuid)
        try:
            # 1. Update status to TRANSCRIBING
            await AutomatedRecordService.update_job_status(
                db, job_uuid, JobStatus.TRANSCRIBING
            )
            try:
                converted_path = audio_path.replace(".webm", ".wav")
                reduced_path = converted_path.replace(".wav", "_reduced.wav")
                directory = Path(reduced_path).parent

                convert_to_wav(audio_path, converted_path)
                reduced_path = split_by_vad(converted_path, directory)
                transcription_chain = TranscriptionChain()
                audio_file_name = await transcription_chain.upload_audio(
                    reduced_path
                )
                await AutomatedRecordService.update_job_status(
                    db,
                    job_uuid,
                    JobStatus.TRANSCRIBED,
                    audio_path=audio_file_name.name,
                )
                return audio_file_name
            except Exception as e:
                await AutomatedRecordService.update_job_status(
                    db, job_uuid, JobStatus.FAILED, error_message=str(e)
                )
                raise e

            finally:
                # Cleanup temporary audio file
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                if os.path.exists(converted_path):
                    os.remove(converted_path)
                if os.path.exists(reduced_path):
                    os.remove(reduced_path)

        except Exception as e:
            logger.error(f"Error processing job {job_uuid}: {e}")
            await AutomatedRecordService.update_job_status(
                db, job_uuid, JobStatus.FAILED, error_message=str(e)
            )
            # Update treatment record status to failed

            try:
                await TreatmentRecordService.update_treatment_record(
                    db,
                    UUID(job.treatment_record_uuid),
                    job.user_uuid,
                    InternalTreatmentRecordUpdate(status=RecordStatus.FAILED),
                )
            except Exception:
                pass

    @staticmethod
    async def generate_transcription(
        db: AsyncSession, file_name: str, job_uuid: UUID
    ) -> str:
        # job = await AutomatedRecordService.get_job(db, job_uuid)
        transcription_chain = TranscriptionChain()
        transcription = await transcription_chain.transcribe(file_name)
        return transcription

    @staticmethod
    async def generate_record(
        db: AsyncSession, transcription: str, job: AutomatedRecordJob
    ) -> str:
        report_list = await TreatmentReportService.get_treatment_reports(
            db=db,
            treatment_uuid=job.treatment_uuid,
            user_uuid=job.user_uuid,
        )
        last_report_context = "Nenhum relatório produzido ainda. Está é a sessão inicial ou uma das sessões iniciais."  # noqa: E501
        if report_list:
            report = report_list[0]  # Use analysis or a summary
            last_report_context = (
                report.demand_description
                + "\n"
                + report.procedures
                + "\n"
                + report.analysis
                + "\n"
                + report.conclusion
            )
        treatment_patient = (
            await PatientWithTreatmentService.get_patient_with_treatment_uuid(
                db=db,
                treatment_uuid=job.treatment_uuid,
                user_uuid=job.user_uuid,
            )
        )

        record_chain = RecordGenerationChain()
        try:
            record_text = await record_chain.generate(
                transcription=transcription,
                gender=treatment_patient.gender,
                context=last_report_context,
            )
            return record_text
        except Exception as e:
            logger.error(e)
