from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models import User
from src.models.auth_session_model import AuthSession
from src.services.auth_service import AuthService


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    return db


class TestAuthService:
    @pytest.mark.asyncio
    @patch("src.services.auth_service.UserService.get_user_by_email")
    @patch("src.services.auth_service.verify_password")
    async def test_authenticate_user_success(
        self, mock_verify, mock_get_user, mock_db
    ):
        mock_user = AsyncMock(spec=User)
        mock_user.hashed_password = "hashed"
        mock_get_user.return_value = mock_user
        mock_verify.return_value = True

        user = await AuthService.authenticate_user(
            mock_db, "test@example.com", "password"
        )

        assert user == mock_user
        mock_get_user.assert_called_once_with(mock_db, "test@example.com")
        mock_verify.assert_called_once_with("password", "hashed")

    @pytest.mark.asyncio
    @patch("src.services.auth_service.UserService.get_user_by_email")
    async def test_authenticate_user_not_found(self, mock_get_user, mock_db):
        mock_get_user.return_value = None

        user = await AuthService.authenticate_user(
            mock_db, "test@example.com", "password"
        )

        assert user is None

    @pytest.mark.asyncio
    @patch("src.services.auth_service.UserService.get_user_by_email")
    @patch("src.services.auth_service.verify_password")
    async def test_authenticate_user_wrong_password(
        self, mock_verify, mock_get_user, mock_db
    ):
        mock_user = AsyncMock(spec=User)
        mock_user.hashed_password = "hashed"
        mock_get_user.return_value = mock_user
        mock_verify.return_value = False

        user = await AuthService.authenticate_user(
            mock_db, "test@example.com", "password"
        )

        assert user is None

    @patch("src.services.auth_service.create_access_token")
    @patch("src.services.auth_service.create_refresh_token")
    def test_create_tokens(self, mock_refresh, mock_access):
        mock_access.return_value = "access"
        mock_refresh.return_value = "refresh"

        tokens = AuthService.create_tokens("user-uuid")

        assert tokens.access_token == "access"
        assert tokens.refresh_token == "refresh"
        assert tokens.token_type == "bearer"
        mock_access.assert_called_once_with(subject="user-uuid")
        mock_refresh.assert_called_once_with(subject="user-uuid")

    @pytest.mark.asyncio
    @patch("src.services.auth_service.settings")
    async def test_create_session(self, mock_settings, mock_db):
        mock_settings.ACCESS_SESSION_EXPIRE_MINUTES = 60

        session = await AuthService.create_session(mock_db, "user-uuid")

        assert isinstance(session, AuthSession)
        assert session.user_uuid == "user-uuid"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_session(self, mock_db):
        await AuthService.delete_session(mock_db, "session-uuid")

        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_generate_csrf_token(self):
        token = AuthService.generate_csrf_token()
        assert len(token) > 0
        assert isinstance(token, str)
