import uuid as uuid_pkg
from http import HTTPStatus

import pytest
from sqlalchemy import select

from src.models import User
from tests.factories import UserFactory

pytestmark = pytest.mark.asyncio


async def test_read_users(session_client):
    client, user = session_client
    response = client.get("/users")
    assert response.status_code == HTTPStatus.OK
    assert isinstance(response.json(), list)


async def test_read_me(session_client):
    client, user = session_client
    response = client.get("/users/me")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["email"] == user.email
    assert data["uuid"] == str(user.uuid)


async def test_read_user_by_uuid(session_client, db_session):
    client, _ = session_client
    other_user = UserFactory.build()
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    response = client.get(f"/users/{other_user.uuid}")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["email"] == other_user.email


async def test_read_user_by_uuid_not_found(session_client):
    client, _ = session_client
    random_uuid = str(uuid_pkg.uuid4())
    response = client.get(f"/users/{random_uuid}")
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "detail" in response.json()


async def test_create_user(client):
    user_data = {
        "email": "newuser@example.com",
        "name": "New User",
        "password": "newpassword123",
        "password_confirmation": "newpassword123",
    }
    response = client.post("/users", json=user_data)
    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data["email"] == user_data["email"]
    assert "uuid" in data


async def test_create_user_preexisting_email(client, db_session):
    user = UserFactory.build(email="olduser@example.com")
    db_session.add(user)
    await db_session.commit()

    user_data = {
        "email": "olduser@example.com",
        "name": "New User",
        "password": "newpassword123",
        "password_confirmation": "newpassword123",
    }
    response = client.post("/users", json=user_data)
    assert response.status_code == HTTPStatus.CONFLICT
    assert "detail" in response.json()


async def test_create_user_with_mismatched_passwords(client):
    user_data = {
        "email": "newuser@example.com",
        "name": "New User",
        "password": "newpassword123",
        "password_confirmation": "mismatchedpassword",
    }
    response = client.post("/users", json=user_data)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "detail" in response.json()


async def test_update_user(session_client):
    client, user = session_client
    update_data = {"name": "Updated Name"}
    response = client.patch(f"/users/{user.uuid}", json=update_data)
    assert response.status_code == HTTPStatus.OK
    assert response.json()["name"] == "Updated Name"


async def test_update_user_password(session_client):
    client, user = session_client
    update_data = {
        "password": "newpassword123",
        "password_confirmation": "newpassword123",
    }
    response = client.patch(f"/users/{user.uuid}", json=update_data)
    assert response.status_code == HTTPStatus.OK


async def test_update_user_password_mismatched(session_client):
    client, user = session_client
    update_data = {
        "password": "newpassword123",
        "password_confirmation": "mismatchedpassword",
    }
    response = client.patch(f"/users/{user.uuid}", json=update_data)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "detail" in response.json()


async def test_update_user_not_found(session_client):
    client, _ = session_client
    update_data = {"name": "Updated Name"}
    random_uuid = str(uuid_pkg.uuid4())
    response = client.patch(f"/users/{random_uuid}", json=update_data)
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "detail" in response.json()


async def test_delete_user(session_client, db_session):
    client, _ = session_client
    # Create a separate user to delete (not the auth user)
    to_delete = UserFactory.build()
    db_session.add(to_delete)
    await db_session.commit()
    await db_session.refresh(to_delete)

    response = client.delete(f"/users/{to_delete.uuid}")
    assert response.status_code == HTTPStatus.OK

    # Verify deleted
    result = await db_session.execute(
        select(User).filter(User.uuid == to_delete.uuid)
    )
    deleted_user = result.scalars().first()
    assert deleted_user is None


async def test_delete_user_not_found(session_client):
    client, _ = session_client
    random_uuid = str(uuid_pkg.uuid4())
    response = client.delete(f"/users/{random_uuid}")
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "detail" in response.json()
