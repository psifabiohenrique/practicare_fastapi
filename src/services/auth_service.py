from sqlalchemy.orm import Session

from models import User
from schemas.token import Token
from security import (
    create_access_token,
    create_refresh_token,
    verify_password,
)
from services.user_service import UserService


class AuthService:
    @staticmethod
    def authenticate_user(
        db: Session, email: str, password: str
    ) -> User | None:
        user = UserService.get_user_by_email(db, email)
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    def create_tokens(user_id: int) -> Token:
        return Token(
            access_token=create_access_token(subject=user_id),
            refresh_token=create_refresh_token(subject=user_id),
            token_type="bearer",
        )
