class DomainError(Exception):
    def __init__(self, message: str):
        self.message = message


class NotFoundError(DomainError):
    pass


class ForbiddenError(DomainError):
    pass


class ValidationError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class UnauthorizedError(DomainError):
    pass
