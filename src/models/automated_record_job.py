import uuid as uuid_pkg
from datetime import datetime
from enum import Enum

from sqlalchemy import UUID as SQLUUID
from sqlalchemy import Column, DateTime, Float, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from src.database import Base


class JobStatus(str, Enum):
    PENDING = "pending"
    TRANSCRIBING = "transcribing"
    TRANSCRIBED = "transcribed"
    GENERATING_RECORD = "generating_record"
    COMPLETED = "completed"
    FAILED = "failed"


class AutomatedRecordJob(Base):
    __tablename__ = "automated_record_jobs"

    uuid = Column(
        SQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid_pkg.uuid4,
        index=True,
    )
    user_uuid = Column(SQLUUID)
    treatment_uuid = Column(SQLUUID)
    treatment_record_uuid = Column(SQLUUID)

    audio_path = Column(String)

    status = Column(SQLEnum(JobStatus), nullable=False)
    error_message = Column(String, nullable=True)

    transcription = Column(String, nullable=True)
    generated_record = Column(String, nullable=True)
    audio_duration_seconds = Column(Float, nullable=True)
    audio_duration_after_vad_seconds = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    treatment_record = relationship(
        "TreatmentRecord", back_populates="automated_record_job"
    )
