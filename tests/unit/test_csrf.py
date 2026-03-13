from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from src.routers.deps import csrf_protect


class _FakeRequest:
    """Minimal Request-like object for testing csrf_protect."""

    def __init__(self, path: str, method: str):
        self.url = MagicMock()
        self.url.path = path
        self.method = method


class TestCSRFProtect:
    @pytest.mark.asyncio
    async def test_skips_safe_methods(self):
        for method in ["GET", "HEAD", "OPTIONS"]:
            request = _FakeRequest("/some/path", method)
            result = await csrf_protect(request, None, None)
            assert result is None

    @pytest.mark.asyncio
    async def test_skips_auth_login(self):
        request = _FakeRequest("/auth/login", "POST")
        result = await csrf_protect(request, None, None)
        assert result is None

    @pytest.mark.asyncio
    async def test_skips_auth_logout(self):
        request = _FakeRequest("/auth/logout", "POST")
        result = await csrf_protect(request, None, None)
        assert result is None

    @pytest.mark.asyncio
    async def test_skips_post_users(self):
        request = _FakeRequest("/users", "POST")
        result = await csrf_protect(request, None, None)
        assert result is None

    @pytest.mark.asyncio
    async def test_rejects_missing_csrf_header(self):
        request = _FakeRequest("/patients-with-treatment", "POST")
        with pytest.raises(HTTPException) as exc_info:
            await csrf_protect(request, None, "cookie_token")
        assert exc_info.value.status_code == 403
        assert "CSRF token missing" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_rejects_missing_csrf_cookie(self):
        request = _FakeRequest("/patients-with-treatment", "POST")
        with pytest.raises(HTTPException) as exc_info:
            await csrf_protect(request, "header_token", None)
        assert exc_info.value.status_code == 403
        assert "CSRF token missing" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_rejects_mismatched_tokens(self):
        request = _FakeRequest("/patients-with-treatment", "POST")
        with pytest.raises(HTTPException) as exc_info:
            await csrf_protect(request, "token_a", "token_b")
        assert exc_info.value.status_code == 403
        assert "Invalid CSRF token" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_passes_when_tokens_match(self):
        request = _FakeRequest("/patients-with-treatment", "POST")
        result = await csrf_protect(request, "same_token", "same_token")
        assert result is None

    @pytest.mark.asyncio
    async def test_rejects_both_missing(self):
        request = _FakeRequest("/treatment-records", "PATCH")
        with pytest.raises(HTTPException) as exc_info:
            await csrf_protect(request, None, None)
        assert exc_info.value.status_code == 403
