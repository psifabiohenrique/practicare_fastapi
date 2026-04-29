import logging
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

from src.core.rate_limit import limiter
from src.database import get_db
from src.schemas.auth_schema import LoginRequest
from src.schemas.message_schema import Details, Message
from src.schemas.token_schema import Token, TokenCSRF, TokenPayload
from src.services.auth_service import AuthService
from src.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
SessionDB = Annotated[AsyncSession, Depends(get_db)]


@router.post("/login", response_model=TokenCSRF)
@limiter.limit(settings.RATE_LIMIT_HIGH)
async def login_session(
    request: Request,
    db: SessionDB,
    response: Response,
    form_data: LoginRequest,
):
    logger.info(f"Tentativa de login para o email: {form_data.email}")
    user = await AuthService.authenticate_user(
        db=db, email=form_data.email, password=form_data.password
    )

    if not user:
        logger.warning(
            f"Falha de autenticação para o email: {form_data.email}"
        )
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
        samesite="none",
    )

    csrf_token = AuthService.generate_csrf_token()
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        secure=True,
        samesite="none",
    )

    logger.info(
        f"Login bem-sucedido para o usuário: {user.uuid}",
        extra={"user_uuid": str(user.uuid)},
    )
    return TokenCSRF(csrf_token=csrf_token)


@router.post("/logout", response_model=Message)
@limiter.limit(settings.RATE_LIMIT_HIGH)
async def logout_session(request: Request, db: SessionDB, response: Response):
    session_uuid = request.cookies.get("session_uuid")
    if session_uuid:
        logger.info(
            f"Logout solicitado para a sessão: {session_uuid}",
            extra={"session_uuid": session_uuid},
        )
        await AuthService.delete_session(db, session_uuid)
    else:
        logger.warning("Logout solicitado sem session_uuid nos cookies")

    response.delete_cookie("session_uuid")
    response.delete_cookie("csrf_token")

    return Message(message="logged_out")


# JTW obsolete routes


@router.post("/login-jwt", response_model=Token)
@limiter.limit(settings.RATE_LIMIT_HIGH)
async def login_jwt(
    request: Request,
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
@limiter.limit(settings.RATE_LIMIT_HIGH)
async def refresh_token_jwt(
    request: Request,
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
@limiter.limit(settings.RATE_LIMIT_HIGH)
async def logout_jwt(request: Request, response: Response) -> any:
    response.delete_cookie("refresh_token")
    return Details(detail="Successfully logged out")
