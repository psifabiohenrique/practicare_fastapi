from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.models import User
from src.services.auth_service import AuthService


@pytest.fixture
def mock_db():
    return AsyncMock()


class TestAuthenticateUser:
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, mock_db):
        mock_user = MagicMock(spec=User)
        mock_user.hashed_password = "hashed_pw"

        with (
            patch(
                "src.services.auth_service.UserService.get_user_by_email",
                return_value=mock_user,
            ),
            patch(
                "src.services.auth_service.verify_password",
                return_value=True,
            ),
        ):
            result = await AuthService.authenticate_user(
                mock_db, "user@example.com", "password"
            )
        assert result == mock_user

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, mock_db):
        mock_user = MagicMock(spec=User)
        mock_user.hashed_password = "hashed_pw"

        with (
            patch(
                "src.services.auth_service.UserService.get_user_by_email",
                return_value=mock_user,
            ),
            patch(
                "src.services.auth_service.verify_password",
                return_value=False,
            ),
        ):
            result = await AuthService.authenticate_user(
                mock_db, "user@example.com", "wrong"
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, mock_db):
        with patch(
            "src.services.auth_service.UserService.get_user_by_email",
            return_value=None,
        ):
            result = await AuthService.authenticate_user(
                mock_db, "noone@example.com", "password"
            )
        assert result is None


class TestCreateSession:
    @pytest.mark.asyncio
    async def test_create_session(self, mock_db):
        user_uuid = uuid4()
        session = await AuthService.create_session(mock_db, user_uuid)

        assert session.user_uuid == user_uuid
        assert session.uuid is not None
        assert session.expires_at is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()


class TestDeleteSession:
    @pytest.mark.asyncio
    async def test_delete_session(self, mock_db):
        session_uuid = str(uuid4())
        await AuthService.delete_session(mock_db, session_uuid)
        mock_db.execute.assert_awaited_once()
        mock_db.commit.assert_awaited_once()


class TestGenerateCSRFToken:
    def test_generate_csrf_token_returns_string(self):
        token = AuthService.generate_csrf_token()
        assert isinstance(token, str)
        assert len(token) > 0

    def test_tokens_are_unique(self):
        t1 = AuthService.generate_csrf_token()
        t2 = AuthService.generate_csrf_token()
        assert t1 != t2
