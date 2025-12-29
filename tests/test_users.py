from http import HTTPStatus

from models import User
from tests.factories import UserFactory


def test_read_users(client, auth_header):
    response = client.get("/users/", headers=auth_header)
    assert response.status_code == HTTPStatus.OK
    assert isinstance(response.json(), list)


def test_read_me(client, auth_header):
    response = client.get("/users/me", headers=auth_header)
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert "email" in data
    assert "uuid" in data


def test_read_user_by_id(client, auth_header):
    user = UserFactory()
    response = client.get(f"/users/{user.id}", headers=auth_header)
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["email"] == user.email
    assert data["uuid"] == str(user.uuid)


def test_read_user_by_id_not_found(client, auth_header):
    response = client.get(f"/users/{1}", headers=auth_header)
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "detail" in response.json()


def test_create_user(client):
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
    assert "id" in data


def test_create_user_preexisting_email(client):
    UserFactory(email="olduser@example.com")
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


def test_create_user_with_mismatched_passwords(client):
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


def test_update_user(client, auth_header):
    user = UserFactory()
    update_data = {"name": "Updated Name"}

    response = client.patch(
        f"/users/{user.id}", json=update_data, headers=auth_header
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json()["name"] == "Updated Name"


def test_update_user_password(client, auth_header):
    user = UserFactory()
    update_data = {
        "password": "newpassword123",
        "password_confirmation": "newpassword123",
    }

    response = client.patch(
        f"/users/{user.id}", json=update_data, headers=auth_header
    )
    assert response.status_code == HTTPStatus.OK


def test_update_user_password_mismatched(client, auth_header):
    user = UserFactory()
    update_data = {
        "password": "newpassword123",
        "password_confirmation": "mismatchedpassword",
    }

    response = client.patch(
        f"/users/{user.id}", json=update_data, headers=auth_header
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    data = response.json()
    assert "detail" in data


def test_update_user_not_found(client, auth_header):
    update_data = {"name": "Updated Name"}
    response = client.patch(
        f"/users/{3}", json=update_data, headers=auth_header
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "detail" in response.json()


def test_delete_user(client, auth_header, db_session):
    user = UserFactory()
    response = client.delete(f"/users/{user.id}", headers=auth_header)
    assert response.status_code == HTTPStatus.OK

    # Verify deleted
    deleted_user = db_session.get(User, user.id)
    assert deleted_user is None


def test_delete_user_not_found(client, auth_header):
    response = client.delete(f"/users/{3}", headers=auth_header)
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "detail" in response.json()
