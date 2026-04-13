from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exceptions import ConflictError, NotFoundError, ValidationError
from src.models import User
from src.schemas.user_schema import UserCreate, UserUpdate
from src.services.user_service import UserService


class TestUserServiceCRUD:
    @pytest.mark.asyncio
    async def test_get_user_by_uuid_success(self, mock_db, mock_user):
        result_mock = MagicMock()
        result_mock.scalars().first.return_value = mock_user
        mock_db.execute.return_value = result_mock

        user = await UserService.get_user_by_uuid(mock_db, "user-uuid")
        assert user == mock_user

    @pytest.mark.asyncio
    async def test_get_user_by_uuid_not_found(self, mock_db):
        result_mock = MagicMock()
        result_mock.scalars().first.return_value = None
        mock_db.execute.return_value = result_mock

        with pytest.raises(NotFoundError, match="User not found"):
            await UserService.get_user_by_uuid(mock_db, "user-uuid")

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, mock_db, mock_user):
        result_mock = MagicMock()
        result_mock.scalars().first.return_value = mock_user
        mock_db.execute.return_value = result_mock

        user = await UserService.get_user_by_email(mock_db, "test@example.com")
        assert user == mock_user

    @pytest.mark.asyncio
    async def test_get_users(self, mock_db, mock_user):
        result_mock = MagicMock()
        result_mock.scalars().all.return_value = [mock_user]
        mock_db.execute.return_value = result_mock

        users = await UserService.get_users(mock_db)
        assert users == [mock_user]

    @pytest.mark.asyncio
    @patch("src.services.user_service.get_password_hash")
    async def test_create_user_success(self, mock_hash, mock_db):
        mock_hash.return_value = "hashed"
        user_in = UserCreate(
            email="new@example.com",
            name="New User",
            password="password",
            password_confirmation="password",
        )

        with patch(
            "src.services.user_service.UserService.get_user_by_email",
            return_value=None,
        ):
            user = await UserService.create_user(mock_db, user_in)

        assert user.email == "new@example.com"
        assert user.name == "New User"
        assert user.hashed_password == "hashed"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_email_exists(self, mock_db, mock_user):
        user_in = UserCreate(
            email="test@example.com",
            name="Test",
            password="pass",
            password_confirmation="pass",
        )

        with patch(
            "src.services.user_service.UserService.get_user_by_email",
            return_value=mock_user,
        ):
            with pytest.raises(
                ConflictError, match="User with this email already exists"
            ):
                await UserService.create_user(mock_db, user_in)

    @pytest.mark.asyncio
    async def test_create_user_password_mismatch(self, mock_db):
        user_in = UserCreate(
            email="test@example.com",
            name="Test",
            password="pass",
            password_confirmation="mismatch",
        )

        with patch(
            "src.services.user_service.UserService.get_user_by_email",
            return_value=None,
        ):
            with pytest.raises(
                ValidationError, match="Passwords do not match"
            ):
                await UserService.create_user(mock_db, user_in)

    @pytest.mark.asyncio
    @patch("src.services.user_service.get_password_hash")
    async def test_update_user_partial(self, mock_hash, mock_db, mock_user):
        user_in = UserUpdate(name="Updated Name")

        with patch(
            "src.services.user_service.UserService.get_user_by_uuid",
            return_value=mock_user,
        ):
            user = await UserService.update_user(mock_db, "user-uuid", user_in)

        assert user.name == "Updated Name"
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.services.user_service.get_password_hash")
    async def test_update_user_password(self, mock_hash, mock_db, mock_user):
        mock_hash.return_value = "new_hashed"
        user_in = UserUpdate(
            password="new_password", password_confirmation="new_password"
        )

        with patch(
            "src.services.user_service.UserService.get_user_by_uuid",
            return_value=mock_user,
        ):
            user = await UserService.update_user(mock_db, "user-uuid", user_in)

        assert user.hashed_password == "new_hashed"
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_password_mismatch(self, mock_db, mock_user):
        user_in = UserUpdate(
            password="new_password", password_confirmation="mismatch"
        )

        with patch(
            "src.services.user_service.UserService.get_user_by_uuid",
            return_value=mock_user,
        ):
            with pytest.raises(
                ValidationError, match="Passwords do not match"
            ):
                await UserService.update_user(mock_db, "user-uuid", user_in)

    @pytest.mark.asyncio
    async def test_delete_user(self, mock_db, mock_user):
        with patch(
            "src.services.user_service.UserService.get_user_by_uuid",
            return_value=mock_user,
        ):
            user = await UserService.delete_user(mock_db, "user-uuid")

        assert user == mock_user
        mock_db.delete.assert_called_once_with(mock_user)
        mock_db.commit.assert_called_once()
