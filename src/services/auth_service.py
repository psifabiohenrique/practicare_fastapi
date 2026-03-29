import logging
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User
from src.models.auth_session_model import AuthSession
from src.schemas.token_schema import Internal_Tokens
from src.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
)
from src.services.user_service import UserService
from src.settings import settings

logger = logging.getLogger(__name__)


class AuthService:
    SESSION_TTL_MINUTES = 120

    @staticmethod
    async def authenticate_user(
        db: AsyncSession, email: str, password: str
    ) -> User | None:
        user = await UserService.get_user_by_email(db, email)
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    def create_tokens(user_uuid: str) -> Internal_Tokens:
        return Internal_Tokens(
            access_token=create_access_token(subject=user_uuid),
            refresh_token=create_refresh_token(subject=user_uuid),
            token_type="bearer",
        )

    @staticmethod
    async def create_session(db: AsyncSession, user_uuid) -> AuthSession:
        logger.info(
            f"Criando nova sessão para o usuário: {user_uuid}",
            extra={"user_uuid": str(user_uuid)},
        )
        now = datetime.now(timezone.utc)

        session = AuthSession(
            uuid=uuid4(),
            user_uuid=user_uuid,
            expires_at=now
            + timedelta(minutes=settings.ACCESS_SESSION_EXPIRE_MINUTES),
            last_accessed_at=now,
        )

        db.add(session)
        await db.commit()
        await db.refresh(session)

        return session

    @staticmethod
    async def delete_session(db: AsyncSession, session_uuid) -> None:
        logger.info(
            f"Deletando sessão: {session_uuid}",
            extra={"session_uuid": str(session_uuid)},
        )
        await db.execute(
            delete(AuthSession).where(AuthSession.uuid == session_uuid)
        )
        await db.commit()

    @staticmethod
    def generate_csrf_token() -> str:
        return secrets.token_urlsafe(32)
