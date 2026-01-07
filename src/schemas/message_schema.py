from pydantic import BaseModel


class Message(BaseModel):
    message: str

    class Config:
        from_attributes = True


class Details(BaseModel):
    detail: str

    class Config:
        from_attributes = True
