import uuid as uuid_pkg
from datetime import datetime
from enum import Enum

from sqlalchemy import UUID as SQLUUID
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer
from sqlalchemy import Enum as SQLEnum

from src.database import Base


class ProcessType(str, Enum):
    TRANSCRIPTION = "TRANSCRIPTION"
    RECORD_GENERATION = "RECORD_GENERATION"
    REPORT_GENERATION = "REPORT_GENERATION"
    CONTEXT_UPDATE = "CONTEXT_UPDATE"


class UsageStatistic(Base):
    __tablename__ = "usage_statistics"

    uuid = Column(
        SQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid_pkg.uuid4,
        index=True,
    )
    user_uuid = Column(
        SQLUUID, ForeignKey("users.uuid"), nullable=False, index=True
    )
    job_uuid = Column(SQLUUID, nullable=True)

    process_type = Column(SQLEnum(ProcessType), nullable=False)

    input_tokens = Column(Integer, default=0, nullable=False)
    output_tokens = Column(Integer, default=0, nullable=False)

    audio_duration_seconds = Column(Float, nullable=True)
    audio_duration_after_vad_seconds = Column(Float, nullable=True)

    created_at = Column(
        DateTime, default=datetime.now, nullable=False, index=True
    )
