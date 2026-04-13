from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException, Request

from src.routers.deps import (
    csrf_protect,
    get_current_user_jwt,
    get_current_user_session,
)


class TestDeps:
    @pytest.mark.asyncio
    async def test_get_current_user_jwt_success(self, mock_db):
        token = "valid-token"
        payload = {"sub": "user-uuid", "type": "access"}
        user = MagicMock()

        result_mock = MagicMock()
        result_mock.scalars().first.return_value = user
        mock_db.execute.return_value = result_mock

        with patch("jwt.decode", return_value=payload):
            result = await get_current_user_jwt(mock_db, token)
            assert result == user

    @pytest.mark.asyncio
    async def test_get_current_user_jwt_invalid_type(self, mock_db):
        token = "valid-token"
        payload = {"sub": "user-uuid", "type": "refresh"}

        with patch("jwt.decode", return_value=payload):
            with pytest.raises(HTTPException) as exc:
                await get_current_user_jwt(mock_db, token)
            assert exc.value.status_code == HTTPStatus.UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_current_user_jwt_decode_error(self, mock_db):
        token = "invalid-token"
        with patch("jwt.decode", side_effect=jwt.PyJWTError("error")):
            with pytest.raises(HTTPException) as exc:
                await get_current_user_jwt(mock_db, token)
            assert exc.value.status_code == HTTPStatus.UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_current_user_jwt_user_not_found(self, mock_db):
        token = "valid-token"
        payload = {"sub": "user-uuid", "type": "access"}

        result_mock = MagicMock()
        result_mock.scalars().first.return_value = None
        mock_db.execute.return_value = result_mock

        with patch("jwt.decode", return_value=payload):
            with pytest.raises(HTTPException) as exc:
                await get_current_user_jwt(mock_db, token)
            assert exc.value.status_code == HTTPStatus.NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_current_user_session_success(self, mock_db):
        request = MagicMock(spec=Request)
        request.cookies = {"session_uuid": "session-uuid"}

        session = MagicMock()
        session.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        session.user_uuid = "user-uuid"

        user = MagicMock()

        res_session = MagicMock()
        res_session.scalars().one_or_none.return_value = session

        res_user = MagicMock()
        res_user.scalars().one_or_none.return_value = user

        mock_db.execute.side_effect = [res_session, res_user]

        result = await get_current_user_session(request, mock_db)
        assert result == user
        assert mock_db.commit.call_count == 1

    @pytest.mark.asyncio
    async def test_get_current_user_session_no_cookie(self, mock_db):
        request = MagicMock(spec=Request)
        request.cookies = {}

        with pytest.raises(HTTPException) as exc:
            await get_current_user_session(request, mock_db)
        assert exc.value.status_code == HTTPStatus.UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_current_user_session_not_found(self, mock_db):
        request = MagicMock(spec=Request)
        request.cookies = {"session_uuid": "session-uuid"}

        res_session = MagicMock()
        res_session.scalars().one_or_none.return_value = None
        mock_db.execute.return_value = res_session

        with pytest.raises(HTTPException) as exc:
            await get_current_user_session(request, mock_db)
        assert exc.value.status_code == HTTPStatus.UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_current_user_session_expired(self, mock_db):
        request = MagicMock(spec=Request)
        request.cookies = {"session_uuid": "session-uuid"}

        session = MagicMock()
        session.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        session.user_uuid = "user-uuid"

        user = MagicMock()

        res_session = MagicMock()
        res_session.scalars().one_or_none.return_value = session

        res_user = MagicMock()
        res_user.scalars().one_or_none.return_value = user

        mock_db.execute.side_effect = [res_session, res_user]

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_session(request, mock_db)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Session expired"
        mock_db.delete.assert_called_once_with(session)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_current_user_session_user_deleted(self, mock_db):
        request = MagicMock(spec=Request)
        request.cookies = {"session_uuid": "session-uuid"}

        session = MagicMock()
        session.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        res_session = MagicMock()
        res_session.scalars().one_or_none.return_value = session

        res_user = MagicMock()
        res_user.scalars().one_or_none.return_value = None

        mock_db.execute.side_effect = [res_session, res_user]

        with pytest.raises(HTTPException) as exc:
            await get_current_user_session(request, mock_db)
        assert exc.value.status_code == HTTPStatus.UNAUTHORIZED
        mock_db.delete.assert_called_once_with(session)

    @pytest.mark.asyncio
    async def test_csrf_protect_exempt_routes(self):
        request = MagicMock(spec=Request)
        request.url.path = "/auth/login"
        await csrf_protect(request)  # Should not raise

        request.url.path = "/auth/logout"
        await csrf_protect(request)  # Should not raise

        request.url.path = "/users"
        request.method = "POST"
        await csrf_protect(request)  # Should not raise

    @pytest.mark.asyncio
    async def test_csrf_protect_safe_methods(self):
        request = MagicMock(spec=Request)
        request.url.path = "/any"
        request.method = "GET"
        await csrf_protect(request)  # Should not raise

    @pytest.mark.asyncio
    async def test_csrf_protect_missing_tokens(self):
        request = MagicMock(spec=Request)
        request.url.path = "/any"
        request.method = "POST"

        with pytest.raises(HTTPException) as exc:
            await csrf_protect(request, csrf_header=None, csrf_cookie="cookie")
        assert exc.value.status_code == HTTPStatus.FORBIDDEN

    @pytest.mark.asyncio
    async def test_csrf_protect_mismatch(self):
        request = MagicMock(spec=Request)
        request.url.path = "/any"
        request.method = "POST"

        with pytest.raises(HTTPException) as exc:
            await csrf_protect(request, csrf_header="header", csrf_cookie="cookie")
        assert exc.value.status_code == HTTPStatus.FORBIDDEN

    @pytest.mark.asyncio
    async def test_csrf_protect_success(self):
        request = MagicMock(spec=Request)
        request.url.path = "/any"
        request.method = "POST"
        await csrf_protect(request, csrf_header="token", csrf_cookie="token")  # Should not raise
