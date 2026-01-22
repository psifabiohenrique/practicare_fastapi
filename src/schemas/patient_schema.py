from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.models import Gender


class PatientBase(BaseModel):
    first_name: str
    last_name: str
    email: str | None = None
    phone: str | None = None
    birth_date: date | None = None
    gender: Gender | None = None


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    birth_date: date | None = None
    gender: Gender | None = None


class PatientRead(PatientBase):
    uuid: UUID
    full_name: str

    model_config = ConfigDict(from_attributes=True)
