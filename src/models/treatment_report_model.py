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
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship

from src.database import Base


class ReportStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class TreatmentReport(Base):
    __tablename__ = "treatment_reports"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(
        SQLUUID, default=lambda: str(uuid_pkg.uuid4()), unique=True, index=True
    )
    treatment_uuid = Column(SQLUUID, ForeignKey("treatments.uuid"))
    automated_report_job_uuid = Column(
        SQLUUID, ForeignKey("automated_report_jobs.uuid")
    )

    status = Column(
        SQLEnum(ReportStatus), default=ReportStatus.READY, nullable=False
    )

    demand_description = Column(String, nullable=True)
    procedures = Column(String, nullable=True)
    analysis = Column(String, nullable=True)
    conclusion = Column(String, nullable=True)

    issue_date = Column(Date)
    start_date_period = Column(Date)
    end_date_period = Column(Date)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )

    treatment = relationship("Treatment", back_populates="treatment_reports")
    automated_report_job = relationship(
        "AutomatedReportJob", back_populates="treatment_report"
    )
