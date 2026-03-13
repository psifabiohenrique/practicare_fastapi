from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.core.exceptions import ConflictError, NotFoundError, ValidationError
from src.models import User
from src.schemas.user_schema import UserCreate, UserUpdate
from src.services.user_service import UserService


@pytest.fixture
def mock_db():
    db = AsyncMock()
    return db


class TestUserServiceCreateUser:
    @pytest.mark.asyncio
    async def test_create_user_success(self, mock_db):
        user_in = UserCreate(
            email="new@example.com",
            name="New User",
            password="password123",
            password_confirmation="password123",
        )

        # Mock: no existing user with this email
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = result_mock

        with patch(
            "src.services.user_service.get_password_hash",
            return_value="hashed_pw",
        ):
            user = await UserService.create_user(mock_db, user_in)

        assert user.email == "new@example.com"
        assert user.name == "New User"
        assert user.hashed_password == "hashed_pw"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, mock_db):
        user_in = UserCreate(
            email="existing@example.com",
            name="User",
            password="pw",
            password_confirmation="pw",
        )

        # Mock: existing user found
        existing_user = MagicMock(spec=User)
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = existing_user
        mock_db.execute.return_value = result_mock

        with pytest.raises(ConflictError, match="already exists"):
            await UserService.create_user(mock_db, user_in)

    @pytest.mark.asyncio
    async def test_create_user_password_mismatch(self, mock_db):
        user_in = UserCreate(
            email="new@example.com",
            name="User",
            password="password1",
            password_confirmation="password2",
        )

        # Mock: no existing user
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = result_mock

        with pytest.raises(ValidationError, match="Passwords do not match"):
            await UserService.create_user(mock_db, user_in)


class TestUserServiceGetUser:
    @pytest.mark.asyncio
    async def test_get_user_by_uuid_found(self, mock_db):
        user_uuid = str(uuid4())
        mock_user = MagicMock(spec=User)
        mock_user.uuid = user_uuid

        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = mock_user
        mock_db.execute.return_value = result_mock

        user = await UserService.get_user_by_uuid(mock_db, user_uuid)
        assert user.uuid == user_uuid

    @pytest.mark.asyncio
    async def test_get_user_by_uuid_not_found(self, mock_db):
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = result_mock

        with pytest.raises(NotFoundError, match="User not found"):
            await UserService.get_user_by_uuid(mock_db, str(uuid4()))

    @pytest.mark.asyncio
    async def test_get_user_by_email_returns_none(self, mock_db):
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = result_mock

        result = await UserService.get_user_by_email(mock_db, "no@user.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_users(self, mock_db):
        mock_users = [MagicMock(spec=User), MagicMock(spec=User)]
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = mock_users
        mock_db.execute.return_value = result_mock

        users = await UserService.get_users(mock_db)
        assert len(users) == 2


class TestUserServiceUpdateUser:
    @pytest.mark.asyncio
    async def test_update_user_success(self, mock_db):
        user_uuid = str(uuid4())
        mock_user = MagicMock(spec=User)
        mock_user.uuid = user_uuid

        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = mock_user
        mock_db.execute.return_value = result_mock

        user_update = UserUpdate(name="Updated Name")
        result = await UserService.update_user(
            mock_db, user_uuid, user_update
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_user_password_mismatch(self, mock_db):
        user_uuid = str(uuid4())
        mock_user = MagicMock(spec=User)
        mock_user.uuid = user_uuid

        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = mock_user
        mock_db.execute.return_value = result_mock

        user_update = UserUpdate(
            password="new_pw", password_confirmation="different_pw"
        )
        with pytest.raises(ValidationError, match="Passwords do not match"):
            await UserService.update_user(mock_db, user_uuid, user_update)


class TestUserServiceDeleteUser:
    @pytest.mark.asyncio
    async def test_delete_user_success(self, mock_db):
        user_uuid = str(uuid4())
        mock_user = MagicMock(spec=User)

        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = mock_user
        mock_db.execute.return_value = result_mock

        result = await UserService.delete_user(mock_db, user_uuid)
        mock_db.delete.assert_awaited_once_with(mock_user)
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, mock_db):
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = result_mock

        with pytest.raises(NotFoundError, match="User not found"):
            await UserService.delete_user(mock_db, str(uuid4()))
