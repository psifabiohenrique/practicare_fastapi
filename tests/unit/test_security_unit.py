import jwt

from src.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from src.settings import settings


class TestPasswordHashing:
    def test_get_password_hash_returns_non_empty_string(self):
        hashed = get_password_hash("mysecretpassword")
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != "mysecretpassword"

    def test_verify_password_correct(self):
        password = "mysecretpassword"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        hashed = get_password_hash("correctpassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_different_passwords_produce_different_hashes(self):
        hash1 = get_password_hash("password1")
        hash2 = get_password_hash("password2")
        assert hash1 != hash2

    def test_same_password_produces_different_hashes(self):
        """Argon2 uses a random salt, so same input → different hashes."""
        hash1 = get_password_hash("samepassword")
        hash2 = get_password_hash("samepassword")
        assert hash1 != hash2
        # But both should verify correctly
        assert verify_password("samepassword", hash1)
        assert verify_password("samepassword", hash2)


class TestJWTGeneration:
    def test_create_access_token(self):
        subject = "test-subject"
        token = create_access_token(subject)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == subject
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_create_refresh_token(self):
        subject = "test-subject"
        token = create_refresh_token(subject)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == subject
        assert payload["type"] == "refresh"
        assert "exp" in payload
