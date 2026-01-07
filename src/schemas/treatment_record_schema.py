from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TreatmentRecordBase(BaseModel):
    treatment_uuid: UUID
    date: datetime
    start_time: datetime
    end_time: datetime
    content: str


class TreatmentRecordCreate(TreatmentRecordBase):
    pass


class TreatmentRecordUpdate(BaseModel):
    date: datetime | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    content: str | None = None


class TreatmentRecordRead(TreatmentRecordBase):
    uuid: UUID
    created_at: datetime
    updated_at: datetime
    record_number: int

    model_config = ConfigDict(from_attributes=True)
