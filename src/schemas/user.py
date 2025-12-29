from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    name: str | None = None


class UserCreate(UserBase):
    password: str
    password_confirmation: str


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    name: str | None = None
    password: str | None = None
    password_confirmation: str | None = None


class UserRead(UserBase):
    id: int
    uuid: UUID

    model_config = ConfigDict(from_attributes=True)
