"""The pagination convention, fixed before the first list endpoint uses it.

No route paginates yet. These tests pin the contract - the page window maths and
the `meta` block - so that catalogue and every list after it inherit a shape that
is already agreed rather than inventing one each.
"""

from __future__ import annotations

import pytest

from app.core.pagination import MAX_PAGE_SIZE, PageParams, total_pages
from app.core.responses import ok, paginated


@pytest.mark.parametrize(
    ("page", "page_size", "offset"),
    [(1, 20, 0), (2, 20, 20), (3, 50, 100)],
)
def test_the_page_window_translates_to_offset_and_limit(page, page_size, offset):
    params = PageParams(page=page, page_size=page_size)

    assert params.offset == offset
    assert params.limit == page_size


@pytest.mark.parametrize(
    ("total_items", "page_size", "expected"),
    [
        (0, 20, 0),  # nothing to page through
        (1, 20, 1),
        (20, 20, 1),  # exactly full
        (21, 20, 2),  # one over
        (4, 3, 2),
    ],
)
def test_total_pages_counts_the_partial_page(total_items, page_size, expected):
    assert total_pages(total_items, page_size) == expected


def test_paginated_reports_the_whole_result_set_not_the_page():
    """`total_items` is what tells a client there is a page 2."""
    response = paginated(
        ["a", "b"], total_items=7, params=PageParams(page=1, page_size=2), message="Listed"
    )

    assert response.success is True
    assert response.message == "Listed"
    assert response.data == ["a", "b"]
    assert response.meta.page == 1
    assert response.meta.page_size == 2
    assert response.meta.total_items == 7
    assert response.meta.total_pages == 4


def test_non_list_responses_carry_no_meta():
    """`meta` is for pages; a single resource must not grow a null page block."""
    assert ok({"id": 1}).meta is None


def test_the_page_size_ceiling_is_defined():
    """An uncapped page_size is a cheap way to make the database do too much."""
    assert MAX_PAGE_SIZE == 100
