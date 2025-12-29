from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError
from sqlalchemy.orm import Session

from database import get_db
from schemas.token import Token, TokenPayload
from services.auth_service import AuthService
from settings import settings

router = APIRouter(prefix="/auth", tags=["auth"])
SessionDB = Annotated[Session, Depends(get_db)]


@router.post("/login", response_model=Token)
def login(
    db: SessionDB,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> any:
    user = AuthService.authenticate_user(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    return AuthService.create_tokens(user.id)


@router.post("/refresh", response_model=Token)
def refresh_token(refresh_token: str, db: SessionDB) -> any:
    try:
        payload = jwt.decode(
            refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)

        if token_data.type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

    except (jwt.PyJWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    return AuthService.create_tokens(int(token_data.sub))
