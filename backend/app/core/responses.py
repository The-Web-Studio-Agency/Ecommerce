"""Standard API response envelope.

Every endpoint returns the same shape:

    {"success": true, "message": "...", "data": {...}}

Errors use the mirrored shape, built by the handlers in `app.main`:

    {"success": false, "message": "...", "error": {"code": "...", "details": [...]}}

Build success responses with `ok()` so the contract stays identical across
modules and is documented correctly in OpenAPI. List endpoints use
`paginated()`, which fills in the `meta` block.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from app.core.pagination import PageParams, total_pages

T = TypeVar("T")


class PageMeta(BaseModel):
    """Where a list response sits in the full result set."""

    page: int
    page_size: int
    total_items: int
    total_pages: int


class ApiResponse(BaseModel, Generic[T]):
    """Successful response envelope."""

    success: bool = True
    message: str = "OK"
    data: T | None = None
    #: Populated for paginated list responses; null everywhere else.
    meta: PageMeta | None = None


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


def paginated(
    items: Sequence[T],
    *,
    total_items: int,
    params: PageParams,
    message: str = "OK",
) -> ApiResponse[list[T]]:
    """Build a success envelope for one page of a list.

    `total_items` is the count of the WHOLE result set, not of `items` - it is
    what lets a client know there is a page 2.
    """
    return ApiResponse[list[T]](
        success=True,
        message=message,
        data=list(items),
        meta=PageMeta(
            page=params.page,
            page_size=params.page_size,
            total_items=total_items,
            total_pages=total_pages(total_items, params.page_size),
        ),
    )
