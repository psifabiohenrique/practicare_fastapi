import pytest

from src.core.exceptions import (
    BadRequestError,
    ConflictError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)


class TestDomainExceptions:
    def test_domain_error_stores_message(self):
        exc = DomainError("something went wrong")
        assert exc.message == "something went wrong"

    def test_not_found_error_is_domain_error(self):
        exc = NotFoundError("resource not found")
        assert isinstance(exc, DomainError)
        assert exc.message == "resource not found"

    def test_forbidden_error_is_domain_error(self):
        exc = ForbiddenError("access denied")
        assert isinstance(exc, DomainError)
        assert exc.message == "access denied"

    def test_validation_error_is_domain_error(self):
        exc = ValidationError("invalid data")
        assert isinstance(exc, DomainError)
        assert exc.message == "invalid data"

    def test_conflict_error_is_domain_error(self):
        exc = ConflictError("already exists")
        assert isinstance(exc, DomainError)
        assert exc.message == "already exists"

    def test_unauthorized_error_is_domain_error(self):
        exc = UnauthorizedError("not authenticated")
        assert isinstance(exc, DomainError)
        assert exc.message == "not authenticated"

    def test_bad_request_error_is_domain_error(self):
        exc = BadRequestError("bad input")
        assert isinstance(exc, DomainError)
        assert exc.message == "bad input"

    def test_exceptions_are_catchable_as_exception(self):
        for exc_cls in [
            NotFoundError,
            ForbiddenError,
            ValidationError,
            ConflictError,
            UnauthorizedError,
            BadRequestError,
        ]:
            with pytest.raises(exc_cls) as exc_info:
                raise exc_cls("test")
            assert str(exc_info.value) == "test"
