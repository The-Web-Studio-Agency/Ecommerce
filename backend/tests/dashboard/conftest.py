"""Fixtures for the dashboard tests.

Dashboard aggregates data across catalogue, orders and payments. Catalogue
data is built through the same API-based factories the catalogue tests use;
orders and payments are inserted directly via `session` since no
order-placement flow is exercised here -- only the aggregation itself.
"""

from __future__ import annotations

import pytest_asyncio

from tests.catalogue.factories import DATA, PRODUCTS, make_category, make_product
from tests.helpers import sample


@pytest_asyncio.fixture(loop_scope="session")
async def category(client, admin_headers) -> dict:
    return await make_category(client, admin_headers)


@pytest_asyncio.fixture(loop_scope="session")
async def product(client, admin_headers, category) -> dict:
    """An ACTIVE product with one image."""
    return await make_product(client, admin_headers, category["id"], status="ACTIVE")


@pytest_asyncio.fixture(loop_scope="session")
async def new_variant(client, admin_headers, product):
    """Factory: `await new_variant(initial_quantity=2, low_stock_threshold=5)`."""
    counter = {"n": 0}

    async def _make(**overrides) -> dict:
        counter["n"] += 1
        payload = sample(DATA, "stocked_variant", **overrides)
        if "sku" not in overrides:
            payload["sku"] = f"DASH-SKU-{counter['n']}"

        response = await client.post(
            f"{PRODUCTS}/{product['id']}/variants", json=payload, headers=admin_headers
        )
        assert response.status_code == 201, response.text
        return response.json()["data"]

    return _make


@pytest_asyncio.fixture(loop_scope="session")
async def variant(new_variant) -> dict:
    """An ACTIVE variant with 10 in stock."""
    return await new_variant()
