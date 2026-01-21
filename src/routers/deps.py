from datetime import datetime, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
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
        select(User).filter(User.id == session.user_id)
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


CurrentUser = Annotated[User, Depends(get_current_user_session)]
