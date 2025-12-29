from http import HTTPStatus

from jwt import decode, encode

from models import User
from security import get_password_hash
from settings import settings


def test_login_success(client, db_session):
    password = "testpassword"

    user = User(
        email="test@example.com",
        name="Test User",
        hashed_password=get_password_hash(password),
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/auth/login", data={"username": user.email, "password": password}
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" not in data
    assert data["token_type"] == "bearer"
    assert "refresh_token" in response.cookies


def test_login_invalid_credentials(client):
    response = client.post(
        "/auth/login",
        data={"username": "wrong@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_refresh_token(client, db_session):
    password = "testpassword"

    user = User(
        email="refresh@example.com",
        name="Refresh User",
        hashed_password=get_password_hash(password),
    )
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/auth/login", data={"username": user.email, "password": password}
    )
    refresh_token = login_response.cookies["refresh_token"]

    client.cookies.set("refresh_token", refresh_token)
    response = client.post("/auth/refresh")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" not in data
    assert "refresh_token" in response.cookies


def test_refresh_token_invalid_type(client, db_session):
    password = "testpassword"

    user = User(
        email="refresh@example.com",
        name="Refresh User",
        hashed_password=get_password_hash(password),
    )
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/auth/login", data={"username": user.email, "password": password}
    )
    refresh_token = login_response.cookies["refresh_token"]
    payload = decode(
        refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
    )
    payload["type"] = "wrong"
    refresh_token = encode(
        payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )

    client.cookies.set("refresh_token", refresh_token)
    response = client.post("/auth/refresh")
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    data = response.json()
    assert "detail" in data


def test_refresh_token_invalid_secret(client):
    payload = {"sub": "1", "type": "refresh"}
    refresh_token = encode(payload, "wrong", algorithm=settings.ALGORITHM)

    client.cookies.set("refresh_token", refresh_token)
    response = client.post("/auth/refresh")
    assert response.status_code == HTTPStatus.FORBIDDEN
    data = response.json()
    assert "detail" in data
