from pydantic import BaseModel, ConfigDict

from utils.enums import Weekdays


class TreatmentBase(BaseModel):
    user_id: str
    patient_id: str
    weekday: Weekdays
    start_time: str
    end_time: str


class TreatmentCreate(TreatmentBase):
    pass


class TreatmentUpdate(BaseModel):
    user_id: str | None = None
    patient_id: str | None = None
    weekday: Weekdays | None = None
    start_time: str | None = None
    end_time: str | None = None


class TreatmentRead(TreatmentBase):
    id: int
    uuid: str

    model_config = ConfigDict(from_attributes=True)
