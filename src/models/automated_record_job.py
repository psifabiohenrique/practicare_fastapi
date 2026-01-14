import uuid as uuid_pkg
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy import Enum as SQLEnum

from database import Base


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
        String, default=lambda: str(uuid_pkg.uuid4()), unique=True, index=True
    )
    user_uuid = Column(String)
    treatment_uuid = Column(String)
    treatment_record_uuid = Column(String)

    audio_path = Column(String)

    status = Column(SQLEnum(JobStatus), nullable=False)
    error_message = Column(String, nullable=True)

    transcription = Column(String, nullable=True)
    generated_record = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )
