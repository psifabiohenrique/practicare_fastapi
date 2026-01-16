from datetime import date as _date
from datetime import datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.models.treatment_record_model import RecordStatus


class TreatmentRecordBase(BaseModel):
    treatment_uuid: UUID
    date: _date
    start_time: time
    end_time: time
    content: str


class TreatmentRecordCreate(TreatmentRecordBase):
    pass


class TreatmentRecordUpdate(BaseModel):
    date: _date | None = None
    start_time: time | None = None
    end_time: time | None = None
    content: str | None = None


class TreatmentRecordRead(TreatmentRecordBase):
    uuid: UUID
    status: RecordStatus
    created_at: datetime
    updated_at: datetime
    record_number: int

    model_config = ConfigDict(from_attributes=True)
