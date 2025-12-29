from http import HTTPStatus

from models import User
from tests.factories import UserFactory


def test_create_user(db_session):
    user = UserFactory()

    assert user.id is not None
    assert user.uuid is not None
    assert user.name is not None
    assert user.email is not None
    assert user.hashed_password is not None

    # Verify persistence
    db_user = db_session.query(User).filter(User.id == user.id).first()
    assert db_user.email == user.email


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"Hello": "World"}
