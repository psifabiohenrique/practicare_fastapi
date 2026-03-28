from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException, Request, Response

from src.routers.auth_controller import (
    login_jwt,
    login_session,
    logout_jwt,
    logout_session,
    refresh_token_jwt,
)
from src.schemas.auth_schema import LoginRequest
from src.schemas.token_schema import Internal_Tokens


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_response():
    res = MagicMock(spec=Response)
    return res


class TestAuthController:
    @pytest.mark.asyncio
    async def test_login_session_success(self, mock_db, mock_response):
        form_data = LoginRequest(email="test@example.com", password="password")
        user = MagicMock()
        user.uuid = "user-uuid"

        session = MagicMock()
        session.uuid = "session-uuid"

        with patch(
            "src.services.auth_service.AuthService.authenticate_user",
            return_value=user,
        ), patch(
            "src.services.auth_service.AuthService.create_session",
            return_value=session,
        ), patch(
            "src.services.auth_service.AuthService.generate_csrf_token",
            return_value="csrf-token",
        ):
            response = await login_session(mock_db, mock_response, form_data)

            assert response.csrf_token == "csrf-token"
            assert mock_response.set_cookie.call_count == 2

    @pytest.mark.asyncio
    async def test_login_session_invalid_credentials(
        self, mock_db, mock_response
    ):
        form_data = LoginRequest(email="test@example.com", password="password")

        with patch(
            "src.services.auth_service.AuthService.authenticate_user",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc:
                await login_session(mock_db, mock_response, form_data)
            assert exc.value.status_code == HTTPStatus.UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_logout_session(self, mock_db, mock_response):
        request = MagicMock(spec=Request)
        request.cookies = {"session_uuid": "session-uuid"}

        with patch(
            "src.services.auth_service.AuthService.delete_session"
        ) as mock_delete:
            response = await logout_session(mock_db, request, mock_response)
            assert response.message == "logged_out"
            mock_delete.assert_called_once_with(mock_db, "session-uuid")
            assert mock_response.delete_cookie.call_count == 2

    @pytest.mark.asyncio
    async def test_login_jwt_success(self, mock_db, mock_response):
        form_data = MagicMock()
        form_data.username = "test@example.com"
        form_data.password = "password"

        user = MagicMock()
        user.uuid = "user-uuid"

        tokens = Internal_Tokens(
            access_token="access", refresh_token="refresh", token_type="bearer"
        )

        with patch(
            "src.services.auth_service.AuthService.authenticate_user",
            return_value=user,
        ), patch(
            "src.services.auth_service.AuthService.create_tokens",
            return_value=tokens,
        ):
            response = await login_jwt(mock_db, mock_response, form_data)
            assert response.access_token == "access"
            mock_response.set_cookie.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_jwt_invalid_credentials(self, mock_db, mock_response):
        form_data = MagicMock()
        form_data.username = "test@example.com"
        form_data.password = "password"

        with patch(
            "src.services.auth_service.AuthService.authenticate_user",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc:
                await login_jwt(mock_db, mock_response, form_data)
            assert exc.value.status_code == HTTPStatus.UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_refresh_token_jwt_success(self, mock_db, mock_response):
        refresh_token = "valid-refresh-token"
        payload = {"sub": "user-uuid", "type": "refresh"}
        tokens = Internal_Tokens(
            access_token="new-access",
            refresh_token="new-refresh",
            token_type="bearer",
        )

        with patch("jwt.decode", return_value=payload), patch(
            "src.services.auth_service.AuthService.create_tokens",
            return_value=tokens,
        ):
            response = await refresh_token_jwt(
                mock_db, mock_response, refresh_token
            )
            assert response.access_token == "new-access"
            mock_response.set_cookie.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_token_jwt_missing(self, mock_db, mock_response):
        with pytest.raises(HTTPException) as exc:
            await refresh_token_jwt(mock_db, mock_response, None)
        assert exc.value.status_code == HTTPStatus.UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_refresh_token_jwt_invalid_type(self, mock_db, mock_response):
        refresh_token = "invalid-type-token"
        payload = {"sub": "user-uuid", "type": "access"}

        with patch("jwt.decode", return_value=payload):
            with pytest.raises(HTTPException) as exc:
                await refresh_token_jwt(mock_db, mock_response, refresh_token)
            assert exc.value.status_code == HTTPStatus.UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_refresh_token_jwt_decode_error(self, mock_db, mock_response):
        refresh_token = "invalid-token"

        with patch("jwt.decode", side_effect=jwt.PyJWTError("Decode error")):
            with pytest.raises(HTTPException) as exc:
                await refresh_token_jwt(mock_db, mock_response, refresh_token)
            assert exc.value.status_code == HTTPStatus.FORBIDDEN

    @pytest.mark.asyncio
    async def test_logout_jwt(self, mock_response):
        response = await logout_jwt(mock_response)
        assert response.detail == "Successfully logged out"
        mock_response.delete_cookie.assert_called_once_with("refresh_token")
