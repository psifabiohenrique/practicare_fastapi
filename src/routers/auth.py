from typing import Annotated

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas.message import Details
from schemas.token import Token, TokenPayload
from services.auth_service import AuthService
from settings import settings

router = APIRouter(prefix="/auth", tags=["auth"])
SessionDB = Annotated[AsyncSession, Depends(get_db)]


@router.post("/login", response_model=Token)
async def login(
    db: SessionDB,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> any:
    user = await AuthService.authenticate_user(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    tokens = AuthService.create_tokens(user.uuid)

    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        httponly=True,
        secure=True,  # Set to False only for local development
        samesite="lax",
    )

    return Token(
        access_token=tokens.access_token,
        token_type=tokens.token_type,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    db: SessionDB,
    response: Response,
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> any:
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )

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

    tokens = AuthService.create_tokens(token_data.sub)

    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
    )

    return Token(
        access_token=tokens.access_token,
        token_type=tokens.token_type,
    )


@router.post("/logout", response_model=Details)
async def logout(response: Response) -> any:
    response.delete_cookie("refresh_token")
    return Details(detail="Successfully logged out")
