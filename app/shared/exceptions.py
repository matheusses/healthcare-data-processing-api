"""Domain and unexpected exceptions for global handling."""


class DomainException(Exception):
    """Business rule violation; mapped to HTTP 400/422."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or "DOMAIN_ERROR"


class UnexpectedException(Exception):
    """Unexpected/system error; mapped to HTTP 500."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundException(Exception):
    """Resource not found; mapped to HTTP 404."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
