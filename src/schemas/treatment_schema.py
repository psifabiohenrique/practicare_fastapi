from datetime import time
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.models import Weekdays


class TreatmentBase(BaseModel):
    user_uuid: UUID
    patient_uuid: UUID
    weekday: Weekdays
    start_time: time
    end_time: time


class TreatmentCreate(TreatmentBase):
    pass


class TreatmentUpdate(BaseModel):
    weekday: Weekdays | None = None
    start_time: time | None = None
    end_time: time | None = None


class TreatmentRead(TreatmentBase):
    uuid: UUID

    model_config = ConfigDict(from_attributes=True)
