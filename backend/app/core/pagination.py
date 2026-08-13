"""Shared pagination inputs for list endpoints."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Query

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class Pagination:
    """Validated page/page_size pair with derived SQL offset/limit."""

    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def pagination_params(
    page: int = Query(1, ge=1, description="1-based page number"),
    page_size: int = Query(
        DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        description=f"Items per page (max {MAX_PAGE_SIZE})",
    ),
) -> Pagination:
    """FastAPI dependency producing validated pagination parameters."""
    return Pagination(page=page, page_size=page_size)
