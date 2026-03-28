from unittest.mock import MagicMock

import pytest
from fastapi import Request

from src.core.exceptions import DomainError, UnauthorizedError
from src.main import domain_exception_handler, unauthorized_exception_handler


@pytest.mark.asyncio
async def test_unauthorized_exception_handler():
    request = MagicMock(spec=Request)
    exc = UnauthorizedError("not authorized")
    response = await unauthorized_exception_handler(request, exc)
    assert response.status_code == 401
    assert response.body == b'{"detail":"not authorized"}'


@pytest.mark.asyncio
async def test_domain_exception_handler():
    request = MagicMock(spec=Request)
    exc = DomainError("domain error")
    response = await domain_exception_handler(request, exc)
    assert response.status_code == 500
    assert response.body == b'{"detail":"domain error"}'
