from datetime import time

from pydantic import BaseModel, ConfigDict

from core.enums import Weekdays


class TreatmentBase(BaseModel):
    user_uuid: str
    patient_uuid: str
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
    uuid: str

    model_config = ConfigDict(from_attributes=True)
