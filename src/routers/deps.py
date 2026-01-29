from datetime import datetime, timezone
from http import HTTPMethod
from typing import Annotated

import jwt
from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.auth_session_model import AuthSession
from src.models.user_model import User
from src.schemas.token_schema import TokenPayload
from src.settings import settings

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")
SessionDB = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user_jwt(
    db: SessionDB, token: str = Depends(reusable_oauth2)
) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)

        if token_data.type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

    except (jwt.PyJWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    result = await db.execute(
        select(User).filter(User.uuid == str(token_data.sub))
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


async def get_current_user_session(request: Request, db: SessionDB) -> User:
    session_uuid = request.cookies.get("session_uuid")
    if not session_uuid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    result = await db.execute(
        select(AuthSession).filter(AuthSession.uuid == session_uuid)
    )
    session = result.scalars().one_or_none()

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session"
        )

    now = datetime.now(timezone.utc)

    if session.expires_at <= now:
        await db.delete(session)
        await db.commit()

    session.last_accessed_at = now
    await db.commit()

    user_result = await db.execute(
        select(User).filter(User.uuid == session.user_uuid)
    )
    user = user_result.scalars().one_or_none()

    if user is None:
        await db.delete(session)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


async def csrf_protect(
    request: Request,
    csrf_header: str | None = Header(None, alias="X-CSRF-Token"),
    csrf_cookie: str | None = Cookie(None, alias="csrf_token"),
) -> None:
    if request.url.path.startswith("/auth/login"):
        return
    if request.url.path.startswith("/auth/logout"):
        return
    if (
        request.url.path.startswith("/users")
        and request.method == HTTPMethod.POST
    ):
        return

    if request.method in SAFE_METHODS:
        return

    if not csrf_header or not csrf_cookie:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing",
        )

    if csrf_header != csrf_cookie:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token",
        )


CurrentUser = Annotated[User, Depends(get_current_user_session)]
