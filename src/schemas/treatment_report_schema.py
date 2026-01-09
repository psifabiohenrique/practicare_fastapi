from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TreatmentReportBase(BaseModel):
    treatment_uuid: UUID
    demand_description: str
    procedures: str
    analysis: str
    conclusion: str
    issue_date: date
    start_date_period: time
    end_date_period: time


class TreatmentReportCreate(TreatmentReportBase):
    pass


class TreatmentReportUpdate(BaseModel):
    demand_description: str | None = None
    procedures: str | None = None
    analysis: str | None = None
    conclusion: str | None = None
    issue_date: date | None = None
    start_date_period: time | None = None
    end_date_period: time | None = None


class TreatmentReportRead(TreatmentReportBase):
    uuid: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
