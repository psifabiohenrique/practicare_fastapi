import uuid as uuid_pkg
from datetime import datetime
from enum import Enum

from sqlalchemy import UUID as SQLUUID
from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from src.database import Base


class RecordStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class TreatmentRecord(Base):
    __tablename__ = "treatment_records"

    __table_args__ = (UniqueConstraint("treatment_uuid", "record_number"),)

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(
        SQLUUID, default=lambda: str(uuid_pkg.uuid4()), unique=True, index=True
    )
    treatment_uuid = Column(SQLUUID, ForeignKey("treatments.uuid"))
    automated_record_job_uuid = Column(
        SQLUUID, ForeignKey("automated_record_jobs.uuid")
    )

    status = Column(
        SQLEnum(RecordStatus), default=RecordStatus.READY, nullable=False
    )
    date = Column(Date)
    start_time = Column(Time)
    end_time = Column(Time)
    content = Column(String)
    record_number = Column(Integer)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )

    treatment = relationship("Treatment", back_populates="treatment_records")
    automated_record_job = relationship(
        "AutomatedRecordJob", back_populates="treatment_record"
    )
