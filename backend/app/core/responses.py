"""Standard API response envelope.

Every endpoint returns the same shape:

    {"success": true, "message": "...", "data": {...}}

Errors use the mirrored shape, built by the handlers in `app.main`:

    {"success": false, "message": "...", "error": {"code": "...", "details": [...]}}

Build success responses with `ok()` so the contract stays identical across
modules and is documented correctly in OpenAPI.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Successful response envelope."""

    success: bool = True
    message: str = "OK"
    data: T | None = None


class ErrorPayload(BaseModel):
    code: str = Field(examples=["NOT_FOUND"])
    details: list[dict[str, Any]] = Field(default_factory=list)
    request_id: str | None = None


class ErrorResponse(BaseModel):
    """Error response envelope."""

    success: bool = False
    message: str = "Request failed"
    error: ErrorPayload


def ok(data: T | None = None, message: str = "OK") -> ApiResponse[T]:
    """Build a success envelope."""
    return ApiResponse[T](success=True, message=message, data=data)
