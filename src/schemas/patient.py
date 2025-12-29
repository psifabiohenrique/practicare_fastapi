from pydantic import BaseModel, ConfigDict


class PatientBase(BaseModel):
    first_name: str
    last_name: str
    email: str | None = None
    phone: str | None = None
    birth_date: str | None = None


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    birth_date: str | None = None


class PatientRead(PatientBase):
    id: int
    uuid: str
    full_name: str

    model_config = ConfigDict(from_attributes=True)
