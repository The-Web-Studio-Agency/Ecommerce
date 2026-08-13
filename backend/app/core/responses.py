"""Standard API response envelope.

Every endpoint in every module returns the same shape:

    {"success": true, "message": "...", "data": {...}, "meta": {...}}

Errors use the mirrored shape:

    {"success": false, "message": "...", "error": {"code": "...", "details": [...]}}

Routers should build responses with `ok()` / `paginated()` so the contract stays
identical across modules and is documented correctly in OpenAPI.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from app.core.pagination import Pagination

T = TypeVar("T")


class PageMeta(BaseModel):
    """Pagination metadata attached to list responses."""

    page: int = Field(ge=1, examples=[1])
    page_size: int = Field(ge=1, examples=[20])
    total_items: int = Field(ge=0, examples=[42])
    total_pages: int = Field(ge=0, examples=[3])


class ApiResponse(BaseModel, Generic[T]):
    """Successful response envelope."""

    success: bool = True
    message: str = "OK"
    data: T | None = None
    meta: PageMeta | None = None


class ErrorPayload(BaseModel):
    code: str = Field(examples=["NOT_FOUND"])
    details: list[dict[str, Any]] = Field(default_factory=list)
    request_id: str | None = None


class ErrorResponse(BaseModel):
    """Error response envelope (documented on every route via `main.py`)."""

    success: bool = False
    message: str = "Request failed"
    error: ErrorPayload


def ok(data: T | None = None, message: str = "OK", meta: PageMeta | None = None) -> ApiResponse[T]:
    """Build a success envelope."""
    return ApiResponse[T](success=True, message=message, data=data, meta=meta)


def page_meta(*, page: int, page_size: int, total_items: int) -> PageMeta:
    """Build pagination metadata from the raw counts."""
    return PageMeta(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=math.ceil(total_items / page_size) if page_size else 0,
    )


def paginated(
    items: T,
    *,
    page: int,
    page_size: int,
    total_items: int,
    message: str = "OK",
) -> ApiResponse[T]:
    """Build a success envelope for a page of results."""
    return ok(
        data=items,
        message=message,
        meta=page_meta(page=page, page_size=page_size, total_items=total_items),
    )


def serialize_page(
    rows: Iterable[Any],
    schema: type[BaseModel],
    *,
    pagination: Pagination,
    total_items: int,
    message: str = "OK",
) -> ApiResponse[Any]:
    """Serialise ORM rows into a paginated envelope.

    Every list endpoint does the same three things - validate each row against
    its read schema, attach pagination metadata, wrap in the envelope - so it is
    written here once instead of in each router.
    """
    return paginated(
        [schema.model_validate(row) for row in rows],
        page=pagination.page,
        page_size=pagination.page_size,
        total_items=total_items,
        message=message,
    )
