import uuid as uuid_pkg
from datetime import datetime
from enum import Enum

from sqlalchemy import UUID as SQLUUID
from sqlalchemy import Column, DateTime, Integer, String
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

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(
        SQLUUID, default=lambda: str(uuid_pkg.uuid4()), unique=True, index=True
    )
    user_uuid = Column(SQLUUID)
    treatment_uuid = Column(SQLUUID)
    treatment_record_uuid = Column(SQLUUID)

    audio_path = Column(String)

    status = Column(SQLEnum(JobStatus), nullable=False)
    error_message = Column(String, nullable=True)

    transcription = Column(String, nullable=True)
    generated_record = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    treatment_record = relationship(
        "TreatmentRecord", back_populates="automated_record_job"
    )
