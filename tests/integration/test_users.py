import uuid as uuid_pkg
from http import HTTPStatus

import pytest
from sqlalchemy import select

from models import User
from tests.factories import UserFactory


@pytest.mark.asyncio
async def test_read_users(user_client):
    client, _, headers = user_client
    response = client.get("/users/", headers=headers)
    assert response.status_code == HTTPStatus.OK
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_read_me(user_client):
    client, user, headers = user_client
    response = client.get("/users/me", headers=headers)
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["email"] == user.email
    assert data["uuid"] == user.uuid


@pytest.mark.asyncio
async def test_read_user_by_uuid(user_client, db_session):
    client, _, headers = user_client
    user = UserFactory.build()
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    response = client.get(f"/users/{user.uuid}", headers=headers)
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["email"] == user.email
    assert data["uuid"] == str(user.uuid)


@pytest.mark.asyncio
async def test_read_user_by_uuid_not_found(user_client):
    client, _, headers = user_client
    random_uuid = str(uuid_pkg.uuid4())
    response = client.get(f"/users/{random_uuid}", headers=headers)
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_create_user(client):
    user_data = {
        "email": "newuser@example.com",
        "name": "New User",
        "password": "newpassword123",
        "password_confirmation": "newpassword123",
    }
    response = client.post("/users/", json=user_data)
    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data["email"] == user_data["email"]
    assert "uuid" in data
    assert "id" not in data


@pytest.mark.asyncio
async def test_create_user_preexisting_email(client, db_session):
    user = UserFactory.build(email="olduser@example.com")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    user_data = {
        "email": "olduser@example.com",
        "name": "New User",
        "password": "newpassword123",
        "password_confirmation": "newpassword123",
    }
    response = client.post("/users/", json=user_data)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_create_user_with_mismatched_passwords(client):
    user_data = {
        "email": "newuser@example.com",
        "name": "New User",
        "password": "newpassword123",
        "password_confirmation": "mismatchedpassword",
    }
    response = client.post("/users/", json=user_data)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_update_user(user_client):
    client, user, headers = user_client
    update_data = {"name": "Updated Name"}

    response = client.patch(
        f"/users/{user.uuid}", json=update_data, headers=headers
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json()["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_update_user_password(user_client):
    client, user, headers = user_client
    update_data = {
        "password": "newpassword123",
        "password_confirmation": "newpassword123",
    }

    response = client.patch(
        f"/users/{user.uuid}", json=update_data, headers=headers
    )
    assert response.status_code == HTTPStatus.OK


@pytest.mark.asyncio
async def test_update_user_password_mismatched(user_client):
    client, user, headers = user_client
    update_data = {
        "password": "newpassword123",
        "password_confirmation": "mismatchedpassword",
    }

    response = client.patch(
        f"/users/{user.uuid}", json=update_data, headers=headers
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_update_user_not_found(user_client):
    client, _, headers = user_client
    update_data = {"name": "Updated Name"}
    random_uuid = str(uuid_pkg.uuid4())
    response = client.patch(
        f"/users/{random_uuid}", json=update_data, headers=headers
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_delete_user(user_client, db_session):
    client, user, headers = user_client
    response = client.delete(f"/users/{user.uuid}", headers=headers)
    assert response.status_code == HTTPStatus.OK

    # Verify deleted
    result = await db_session.execute(
        select(User).filter(User.uuid == user.uuid)
    )
    deleted_user = result.scalars().first()
    assert deleted_user is None


@pytest.mark.asyncio
async def test_delete_user_not_found(user_client):
    client, _, headers = user_client
    random_uuid = str(uuid_pkg.uuid4())
    response = client.delete(f"/users/{random_uuid}", headers=headers)
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "detail" in response.json()
