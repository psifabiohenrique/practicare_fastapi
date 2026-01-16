from datetime import date, datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReportStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class TreatmentReportBase(BaseModel):
    treatment_uuid: UUID
    demand_description: str
    procedures: str
    analysis: str
    conclusion: str
    issue_date: date
    start_date_period: date
    end_date_period: date
    status: ReportStatus = ReportStatus.READY


class TreatmentReportCreate(TreatmentReportBase):
    pass


class AutomatedReportCreate(BaseModel):
    treatment_uuid: UUID
    issue_date: date
    start_date_period: date
    end_date_period: date


class TreatmentReportUpdate(BaseModel):
    demand_description: str | None = None
    procedures: str | None = None
    analysis: str | None = None
    conclusion: str | None = None
    issue_date: date | None = None
    start_date_period: date | None = None
    end_date_period: date | None = None


class InternalTreatmentReportUpdate(TreatmentReportUpdate):
    status: ReportStatus | None = None


class TreatmentReportRead(TreatmentReportBase):
    uuid: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
