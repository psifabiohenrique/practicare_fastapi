from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.chains.record_generation import RecordGenerationChain
from src.ai.chains.transcription import TranscriptionChain
from src.core.exceptions import NotFoundError
from src.models.automated_record_job import AutomatedRecordJob, JobStatus


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
        error_message: str | None = None,
    ):
        job = await AutomatedRecordService.get_job(db, job_uuid)

        job.status = status
        job.error_message = error_message
        await db.commit()
        await db.refresh(job)

        return job

    async def generate_record(
        db: AsyncSession, transcription: str, job_uuid: UUID
    ) -> str:
        record_chain = RecordGenerationChain()
        try:
            record_text = await record_chain.generate(
                transcription=transcription
            )
            return record_text
        except Exception as e:
            await AutomatedRecordService.update_job_status(
                db=db,
                job_uuid=job_uuid,
                status=JobStatus.FAILED,
            )
            raise e

    async def generate_transcription(
        db: AsyncSession, audio: bytes, job_uuid: UUID
    ):
        transcription_chain = TranscriptionChain()
        try:
            transcription = await transcription_chain.transcribe(
                audio_bytes=audio
            )
            return transcription
        except Exception as e:
            await AutomatedRecordService.update_job_status(
                db=db,
                job_uuid=job_uuid,
                status=JobStatus.FAILED,
            )
            raise e
