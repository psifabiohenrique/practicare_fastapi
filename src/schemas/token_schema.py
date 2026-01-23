from pydantic import BaseModel


class Internal_Tokens(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    sub: str | None = None
    type: str | None = None


class TokenCSRF(BaseModel):
    csrf_token: str
