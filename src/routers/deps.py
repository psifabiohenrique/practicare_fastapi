from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User
from schemas.token_schema import TokenPayload
from services.user_service import UserService
from settings import settings

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")
SessionDB = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
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
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    user = await UserService.get_user_by_uuid(db, user_uuid=token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
