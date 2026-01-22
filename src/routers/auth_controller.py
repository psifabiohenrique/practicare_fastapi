from typing import Annotated

import jwt
from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.schemas.auth_schema import LoginRequest
from src.schemas.message_schema import Details, Message
from src.schemas.token_schema import Token, TokenPayload
from src.services.auth_service import AuthService
from src.settings import settings

router = APIRouter(prefix="/auth", tags=["auth"])
SessionDB = Annotated[AsyncSession, Depends(get_db)]


@router.post("/login", response_model=Message)
async def login_session(
    db: SessionDB,
    response: Response,
    form_data: LoginRequest,
):
    user = await AuthService.authenticate_user(
        db=db, email=form_data.email, password=form_data.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    session = await AuthService.create_session(db=db, user_uuid=user.uuid)

    response.set_cookie(
        key="session_uuid",
        value=str(session.uuid),
        httponly=True,
        secure=True,
        samesite="lax",
    )

    csrf_token = AuthService.generate_csrf_token()
    response.set_cookie(
        key="csrf_token", value=csrf_token, httponly=False, samesite="lax"
    )

    return Message(message="Logged_in")


@router.post("/logout", response_model=Message)
async def logout_session(db: SessionDB, request=Request, response=Response):
    session_uuid = request.cookies.get("session_uuid")
    if session_uuid:
        await AuthService.delete_session(db, session_uuid)

    response.delete_cookie("session_uuid")
    response.delete_cookie("csrf_token")

    return Message(message="logged_out")


# JTW obsolete routes


@router.post("/login-jwt", response_model=Token)
async def login_jwt(
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


@router.post("/refresh-jwt", response_model=Token)
async def refresh_token_jwt(
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


@router.post("/logout-jwt", response_model=Details)
async def logout_jwt(response: Response) -> any:
    response.delete_cookie("refresh_token")
    return Details(detail="Successfully logged out")
