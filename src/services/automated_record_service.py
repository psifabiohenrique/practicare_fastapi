import logging
import os
import shutil
import tempfile
from datetime import date
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.ai_result import AIResult
from src.ai.chains.record_generation import RecordGenerationChain
from src.ai.chains.transcription import TranscriptionChain
from src.core.exceptions import NotFoundError
from src.models.automated_record_job import AutomatedRecordJob, JobStatus
from src.models.treatment_record_model import RecordStatus
from src.models.usage_statistic import ProcessType
from src.schemas.dashboard_schema import UsageStatisticCreate
from src.schemas.treatment_record_schema import (
    InternalTreatmentRecordUpdate,
    TreatmentRecordCreate,
)
from src.services.patient_with_treatment_service import (
    PatientWithTreatmentService,
)
from src.services.treatment_record_service import (
    TreatmentRecordService,
)
from src.services.treatment_report_service import TreatmentReportService
from src.services.treatment_service import TreatmentService
from src.services.usage_statistic_service import UsageStatisticService
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
        logger.info(
            "Novo job de prontuário criado",
            extra={
                "job_uuid": str(job.uuid),
                "treatment_uuid": str(treatment_uuid),
                "user_uuid": user_uuid,
            },
        )
        return job

    @staticmethod
    async def initialize_job(
        db: AsyncSession,
        user_uuid: str,
        treatment_uuid: UUID | None = None,
        treatment_record_uuid: UUID | None = None,
        session_date: date | None = None,
    ):
        if treatment_record_uuid:
            record = await TreatmentRecordService.get_treatment_record(
                db=db,
                treatment_record_uuid=treatment_record_uuid,
                user_uuid=user_uuid,
            )
        else:
            treatment = await TreatmentService.get_treatment_by_uuid(
                db=db, treatment_uuid=treatment_uuid, user_uuid=user_uuid
            )
            record = await TreatmentRecordService.create_treatment_record(
                db=db,
                schema=TreatmentRecordCreate(
                    treatment_uuid=treatment_uuid,
                    date=session_date,
                    start_time=treatment.start_time,
                    end_time=treatment.end_time,
                    content="Processando áudio e gerando prontuário...",
                ),
                user_uuid=user_uuid,
            )

        job = await AutomatedRecordService.create_job(
            db=db,
            treatment_uuid=record.treatment_uuid,
            user_uuid=user_uuid,
            treatment_record_uuid=record.uuid,
        )

        return record, job

    @staticmethod
    async def prepare_chunk_dir(job_uuid: UUID) -> Path:
        chunk_dir = Path(tempfile.gettempdir()) / f"chunks_{job_uuid}"
        chunk_dir.mkdir(parents=True, exist_ok=True)
        return chunk_dir

    @staticmethod
    async def save_audio_chunk(
        job_uuid: UUID, chunk_index: int, chunk_data: bytes
    ):
        chunk_dir = await AutomatedRecordService.prepare_chunk_dir(job_uuid)
        chunk_path = chunk_dir / f"chunk_{chunk_index:05d}"
        with open(chunk_path, "wb") as f:
            f.write(chunk_data)

    @staticmethod
    async def finalize_chunked_upload(
        db: AsyncSession, job_uuid: UUID, total_chunks: int
    ) -> str:
        chunk_dir = await AutomatedRecordService.prepare_chunk_dir(job_uuid)
        chunks = sorted(list(chunk_dir.glob("chunk_*")))

        if len(chunks) != total_chunks:
            raise ValueError(
                f"Missing chunks. Expected {total_chunks}, got {len(chunks)}"
            )

        final_path = Path(tempfile.gettempdir()) / f"audio_{job_uuid}.webm"
        with open(final_path, "wb") as outfile:
            for chunk_file in chunks:
                with open(chunk_file, "rb") as infile:
                    shutil.copyfileobj(infile, outfile)

        # Cleanup chunks
        shutil.rmtree(chunk_dir)

        return str(final_path)

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
    async def update_job_status(  # noqa: PLR0913, PLR0917
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
        db: AsyncSession,
        job_uuid: UUID,
        audio_path: str,
    ):
        """
        Main background task for processing an automated record job.
        """
        job = await AutomatedRecordService.get_job(db, job_uuid)
        converted_path = audio_path.replace(".webm", ".wav")
        reduced_path = None

        try:
            # 1. Update status to TRANSCRIBING
            await AutomatedRecordService.update_job_status(
                db, job_uuid, JobStatus.TRANSCRIBING
            )

            directory = Path(converted_path).parent
            convert_to_wav(audio_path, converted_path)
            vad_result = split_by_vad(converted_path, directory)
            reduced_path = vad_result.output_path

            # Store durations on the job for later use
            job.audio_duration_seconds = vad_result.original_duration_seconds
            job.audio_duration_after_vad_seconds = (
                vad_result.vad_duration_seconds
            )

            transcription_chain = TranscriptionChain()
            audio_file_name = await transcription_chain.upload_audio(
                reduced_path
            )

            if not audio_file_name or not audio_file_name.name:
                raise NotFoundError("Audio file name is missing after upload.")

            await AutomatedRecordService.update_job_status(
                db,
                job_uuid,
                JobStatus.TRANSCRIBED,
                audio_path=audio_file_name.name,
            )
            return audio_file_name

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
            raise e

        finally:
            # Cleanup temporary audio files
            if os.path.exists(audio_path):
                os.remove(audio_path)
            if os.path.exists(converted_path):
                os.remove(converted_path)
            if reduced_path and os.path.exists(reduced_path):
                os.remove(reduced_path)

    @staticmethod
    async def generate_transcription(
        db: AsyncSession, file_name: str, job_uuid: UUID
    ) -> AIResult:
        job = await AutomatedRecordService.get_job(db, job_uuid)
        transcription_chain = TranscriptionChain()
        result = await transcription_chain.transcribe(file_name)

        # Save transcription usage statistic
        await UsageStatisticService.create_statistic(
            db,
            UsageStatisticCreate(
                user_uuid=str(job.user_uuid),
                job_uuid=str(job.uuid),
                process_type=ProcessType.TRANSCRIPTION,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                audio_duration_seconds=getattr(
                    job, "audio_duration_seconds", None
                ),
                audio_duration_after_vad_seconds=getattr(
                    job, "audio_duration_after_vad_seconds", None
                ),
            ),
        )

        return result

    @staticmethod
    async def generate_record(
        db: AsyncSession, transcription: str, job: AutomatedRecordJob
    ) -> AIResult:
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
            result = await record_chain.generate(
                transcription=transcription,
                gender=treatment_patient.gender,
                context=last_report_context,
            )

            # Save record generation usage statistic
            await UsageStatisticService.create_statistic(
                db,
                UsageStatisticCreate(
                    user_uuid=str(job.user_uuid),
                    job_uuid=str(job.uuid),
                    process_type=ProcessType.RECORD_GENERATION,
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                ),
            )

            return result
        except Exception as e:
            logger.error(e)
