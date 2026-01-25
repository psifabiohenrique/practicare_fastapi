import logging
import os
import shutil
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
    ):
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
        job.status = status
        if error_message:
            job.error_message = error_message
        if transcription:
            job.transcription = transcription
        await db.commit()
        await db.refresh(job)
        return job

    @staticmethod
    async def process_automated_record_job(
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
            print("#1")

            # 2. Split audio if needed
            logger.info("Enviando áudio para o split")
            temp_dir = f"temp_audio_{str(job_uuid)}"
            os.makedirs(temp_dir, exist_ok=True)
            print("#2")
            try:
                # chunks = split_audio(audio_path, temp_dir, max_size_mb=20)
                converted_audio_path = convert_to_wav(
                    audio_path, f"{temp_dir}/converted.wav"
                )
                print(f'Arquivo convertido: {converted_audio_path}')
                chunks = split_by_vad(converted_audio_path, temp_dir)
                print(f'Chunks separados: {chunks}')
                # 3. Transcribe each chunk
                logger.info("Enviando áudio para a transcrição")
                transcription_chain = TranscriptionChain()
                full_transcription = ""
                for chunk in chunks:
                    with open(chunk, "rb") as f:
                        audio_content = f.read()

                    chunk_transcription = await transcription_chain.transcribe(
                        audio_content=audio_content,
                        filename=os.path.basename(chunk),
                    )
                    full_transcription += chunk_transcription + " "

                full_transcription = full_transcription.strip()
                logger.info("Transcrição de áudio recebida")
                print("#3")
                await AutomatedRecordService.update_job_status(
                    db,
                    job_uuid,
                    JobStatus.TRANSCRIBED,
                    transcription=full_transcription,
                )
                print("#3.5")

                # 4. Generate record
                await AutomatedRecordService.update_job_status(
                    db, job_uuid, JobStatus.GENERATING_RECORD
                )
                print("#4")

                logger.info("Enviando transcrição para geração de prontuário")
                record_text = await AutomatedRecordService.generate_record(
                    db, full_transcription, job
                )
                logger.info("Prontuário recebido")
                print("#4.5")
                # 5. Complete job
                await AutomatedRecordService.update_job_status(
                    db,
                    job_uuid,
                    JobStatus.COMPLETED,
                )
                print("#5")

                # Update the treatment record content

                await TreatmentRecordService.update_treatment_record(
                    db,
                    job.treatment_record_uuid,
                    job.user_uuid,
                    InternalTreatmentRecordUpdate(
                        content=record_text, status=RecordStatus.READY
                    ),
                )
                print("#5.5")

            finally:
                # Cleanup
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                if os.path.exists(audio_path):
                    os.remove(audio_path)

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
    async def generate_record(
        db: AsyncSession, transcription: str, job: AutomatedRecordJob
    ) -> str:
        report_list = await TreatmentReportService.get_treatment_reports(
            db=db,
            treatment_uuid=job.treatment_uuid,
            user_uuid=job.user_uuid,
        )
        print("record: #1")
        last_report_context = "Nenhum relatório produzido ainda. Está é a sessão inicial ou uma das sessões iniciais."  # noqa: E501
        if report_list:
            last_report_context = report_list[
                0
            ].analysis  # Use analysis or a summary
        print("record: #2")
        treatment_patient = (
            await PatientWithTreatmentService.get_patient_with_treatment_uuid(
                db=db,
                treatment_uuid=job.treatment_uuid,
                user_uuid=job.user_uuid,
            )
        )
        print("record: #3")

        record_chain = RecordGenerationChain()
        try:
            record_text = await record_chain.generate(
                transcription=transcription,
                gender=treatment_patient.gender,
                context=last_report_context,
            )
        except Exception as e:
            print(e)
        print("record: #4")
        return record_text
