from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User
from src.schemas.token_schema import Internal_Tokens
from src.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
)
from src.services.user_service import UserService


class AuthService:
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
