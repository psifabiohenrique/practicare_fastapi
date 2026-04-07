from datetime import date, datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReportStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class ReportType(str, Enum):
    COMPLETO = "COMPLETO"
    PERIODICO = "PERIODICO"
    FOCADO = "FOCADO"


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
    report_type: ReportType = ReportType.PERIODICO
    system_prompt: str | None = None


class TreatmentReportCreate(TreatmentReportBase):
    pass


class AutomatedReportCreate(BaseModel):
    report_type: ReportType = ReportType.PERIODICO
    start_date_period: date | None = None
    end_date_period: date | None = None
    system_prompt: str | None = None


class TreatmentReportUpdate(BaseModel):
    demand_description: str | None = None
    procedures: str | None = None
    analysis: str | None = None
    conclusion: str | None = None
    issue_date: date | None = None
    start_date_period: date | None = None
    end_date_period: date | None = None
    report_type: ReportType | None = None
    system_prompt: str | None = None


class InternalTreatmentReportUpdate(TreatmentReportUpdate):
    status: ReportStatus | None = None


class TreatmentReportRead(TreatmentReportBase):
    uuid: UUID
    created_at: datetime
    updated_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
