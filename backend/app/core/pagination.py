"""Pagination convention for list endpoints.

One convention, fixed before the first list endpoint exists, so that every
admin list in the platform pages the same way and clients can be written
against a single shape.

Offset pagination (`?page=1&page_size=20`) is what admin lists need: they are
small, they are sorted by whatever column the operator clicked, and they need a
total so the UI can render "page 3 of 12". Cursor pagination solves a different
problem (deep pagination over a large, append-heavy table) and can be added for
a specific endpoint that actually has it.

`page_size` is capped: without a ceiling, `?page_size=1000000` is a cheap way to
make the database materialise an entire tenant's catalogue in one request.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Query

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class PageParams:
    """A validated page request, translated to SQL offset/limit."""

    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def page_params(
    page: int = Query(1, ge=1, description="1-based page number"),
    page_size: int = Query(
        DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        description=f"Items per page (max {MAX_PAGE_SIZE})",
    ),
) -> PageParams:
    """Route dependency supplying the page window.

    Usage:

        @router.get("/products")
        async def list_products(page: PageParams = Depends(page_params)): ...
    """
    return PageParams(page=page, page_size=page_size)


def total_pages(total_items: int, page_size: int) -> int:
    """Number of pages a result set spans. Zero items is zero pages."""
    return (total_items + page_size - 1) // page_size
