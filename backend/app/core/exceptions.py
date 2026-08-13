"""Application exception hierarchy.

Services raise these; the API layer converts them into the standard error
envelope (see `app.core.responses` and the handlers in `app.main`).
Nothing below ever carries a stack trace or internal detail to the client.
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for expected, client-reportable application errors."""

    status_code: int = 400
    error_code: str = "BAD_REQUEST"
    default_message: str = "Request could not be processed"

    def __init__(
        self,
        message: str | None = None,
        *,
        details: list[dict[str, Any]] | None = None,
        error_code: str | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = details or []
        if error_code:
            self.error_code = error_code
        super().__init__(self.message)


class ValidationFailedError(AppError):
    """Input was syntactically valid but violates a business validation rule."""

    status_code = 422
    error_code = "VALIDATION_ERROR"
    default_message = "Validation failed"


class NotFoundError(AppError):
    status_code = 404
    error_code = "NOT_FOUND"
    default_message = "Resource not found"


class ConflictError(AppError):
    """Uniqueness or state conflict (duplicate email, slug, SKU...)."""

    status_code = 409
    error_code = "CONFLICT"
    default_message = "Resource conflict"


class AuthenticationError(AppError):
    status_code = 401
    error_code = "AUTHENTICATION_FAILED"
    default_message = "Authentication failed"


class PermissionDeniedError(AppError):
    status_code = 403
    error_code = "PERMISSION_DENIED"
    default_message = "You do not have permission to perform this action"


class TenantContextError(AppError):
    """The request could not be resolved to exactly one active tenant."""

    status_code = 400
    error_code = "TENANT_CONTEXT_REQUIRED"
    default_message = "Tenant context could not be resolved for this request"


class RateLimitedError(AppError):
    """The caller exceeded an endpoint's request budget."""

    status_code = 429
    error_code = "RATE_LIMITED"
    default_message = "Too many requests. Please try again later."

    def __init__(
        self,
        message: str | None = None,
        *,
        retry_after_seconds: int | None = None,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message, details=details)
        self.retry_after_seconds = retry_after_seconds
