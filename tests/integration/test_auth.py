from http import HTTPStatus

import pytest

from src.models import User
from src.security import get_password_hash

pytestmark = pytest.mark.asyncio


# ---- Session-based auth tests (current) ----


async def test_session_login_success(client, db_session):
    password = "testpassword"
    user = User(
        email="session@example.com",
        name="Session User",
        hashed_password=get_password_hash(password),
    )
    db_session.add(user)
    await db_session.commit()

    response = client.post(
        "/auth/login",
        json={"email": "session@example.com", "password": password},
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert "csrf_token" in data
    assert "session_uuid" in response.cookies
    assert "csrf_token" in response.cookies


async def test_session_login_invalid_credentials(client):
    response = client.post(
        "/auth/login",
        json={"email": "wrong@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test_session_logout(client, db_session):
    password = "testpassword"
    user = User(
        email="logout-session@example.com",
        name="Logout User",
        hashed_password=get_password_hash(password),
    )
    db_session.add(user)
    await db_session.commit()

    # Login
    login_response = client.post(
        "/auth/login",
        json={"email": user.email, "password": password},
    )
    assert "session_uuid" in login_response.cookies

    # Set cookies for logout
    client.cookies.set("session_uuid", login_response.cookies["session_uuid"])

    # Logout
    response = client.post("/auth/logout")
    assert response.status_code == HTTPStatus.OK
    assert response.json()["message"] == "logged_out"


async def test_session_login_missing_email(client):
    response = client.post(
        "/auth/login",
        json={"password": "test"},
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


async def test_session_login_invalid_email_format(client):
    response = client.post(
        "/auth/login",
        json={"email": "not-an-email", "password": "test"},
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


# ---- JWT auth tests (deprecated/legacy) ----


@pytest.mark.skip(reason="JWT authentication is deprecated")
async def test_login_jwt_success(client, db_session):
    """Deprecated: Tests legacy JWT login endpoint."""
    password = "testpassword"
    user = User(
        email="jwt@example.com",
        name="JWT User",
        hashed_password=get_password_hash(password),
    )
    db_session.add(user)
    await db_session.commit()

    response = client.post(
        "/auth/login-jwt",
        data={"username": user.email, "password": password},
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "refresh_token" in response.cookies


@pytest.mark.skip(reason="JWT authentication is deprecated")
async def test_login_jwt_invalid_credentials(client):
    """Deprecated: Tests legacy JWT login failure."""
    response = client.post(
        "/auth/login-jwt",
        data={"username": "wrong@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.skip(reason="JWT authentication is deprecated")
async def test_logout_jwt(client):
    """Deprecated: Tests legacy JWT logout endpoint."""
    response = client.post("/auth/logout-jwt")
    assert response.status_code == HTTPStatus.OK
    assert response.json()["detail"] == "Successfully logged out"
