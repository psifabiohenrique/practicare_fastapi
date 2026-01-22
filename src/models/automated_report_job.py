import uuid as uuid_pkg
from datetime import datetime
from enum import Enum

from sqlalchemy import UUID as SQLUUID
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from src.database import Base


class ReportJobStatus(str, Enum):
    PENDING = "pending"
    GENERATING_REPORT = "generating_report"
    COMPLETED = "completed"
    FAILED = "failed"


class AutomatedReportJob(Base):
    __tablename__ = "automated_report_jobs"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(
        SQLUUID, default=lambda: str(uuid_pkg.uuid4()), unique=True, index=True
    )
    user_uuid = Column(SQLUUID)
    treatment_uuid = Column(SQLUUID)
    treatment_report_uuid = Column(SQLUUID)

    status = Column(SQLEnum(ReportJobStatus), nullable=False)
    error_message = Column(String, nullable=True)

    generated_report_json = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    treatment_report = relationship(
        "TreatmentReport", back_populates="automated_report_job"
    )
