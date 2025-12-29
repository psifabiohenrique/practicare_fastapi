from http import HTTPStatus

import jwt
import pytest
from fastapi import HTTPException

from routers.deps import get_current_user
from security import create_access_token, create_refresh_token
from settings import settings


def test_get_current_user_valid_token(db_session, user):
    access_token = create_access_token(subject=user.id)
    current_user = get_current_user(db=db_session, token=access_token)
    assert current_user.id == user.id


def test_get_current_user_invalid_token_type(db_session, user):
    refresh_token = create_refresh_token(subject=user.id)
    with pytest.raises(HTTPException) as exc:
        get_current_user(db=db_session, token=refresh_token)
    assert exc.value.status_code == HTTPStatus.UNAUTHORIZED
    assert exc.value.detail == "Invalid token type"


def test_get_current_user_invalid_signature(db_session):
    payload = {"sub": "1", "type": "access"}
    token = jwt.encode(payload, "wrong_secret", algorithm=settings.ALGORITHM)
    with pytest.raises(HTTPException) as exc:
        get_current_user(db=db_session, token=token)
    assert exc.value.status_code == HTTPStatus.FORBIDDEN
    assert exc.value.detail == "Could not validate credentials"


def test_get_current_user_expired_token(db_session):
    # Manually create an expired token
    payload = {"sub": "1", "type": "access", "exp": 1}  # Epoch 1
    token = jwt.encode(
        payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    with pytest.raises(HTTPException) as exc:
        get_current_user(db=db_session, token=token)
    assert exc.value.status_code == HTTPStatus.FORBIDDEN


def test_get_current_user_not_found(db_session):
    token = create_access_token(subject=999)
    with pytest.raises(HTTPException) as exc:
        get_current_user(db=db_session, token=token)
    assert exc.value.status_code == HTTPStatus.NOT_FOUND
    assert exc.value.detail == "User not found"
