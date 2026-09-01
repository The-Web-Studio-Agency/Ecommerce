"""Fixtures for search, sort, and filter tests."""

from __future__ import annotations

import pytest
import pytest_asyncio

from tests.catalogue.factories import make_category, make_product
from tests.conftest import headers_for
from tests.helpers import load_data, sample

DATA = load_data(__file__)

SEARCH = DATA["routes"]["search"]
PRODUCTS = DATA["routes"]["products"]


@pytest_asyncio.fixture(loop_scope="session")
async def search_shopper(make_user, tenant):
    return await make_user(tenant=tenant, phone="+919822224001")


@pytest.fixture
def search_auth(search_shopper) -> dict[str, str]:
    return headers_for(search_shopper)


@pytest_asyncio.fixture(loop_scope="session")
async def search_test_catalogue(client, admin_headers):
    """Sets up a diverse catalogue for testing search, sort, and filters."""
    category = await make_category(client, admin_headers, name="Apparel")
    
    product_data = [
        {"name": "Running Sneaker", "price": "1499.00", "brand": "Nike"},
        {"name": "Cotton T-Shirt", "price": "499.00", "brand": "Puma"},
        {"name": "Formal Shirt", "price": "999.00", "brand": "Adidas"},
    ]
    
    created = []
    for item in product_data:
        prod = await make_product(client, admin_headers, category["id"], name=item["name"], status="ACTIVE")
        payload = sample(DATA, "variant")
        payload["sku"] = f"SRCH-SKU-{item['name'][:3].upper()}"
        payload["price"] = item["price"]
        response = await client.post(
            f"{PRODUCTS}/{prod['id']}/variants", json=payload, headers=admin_headers
        )
        assert response.status_code == 201, response.text
        created.append(response.json()["data"])
        
    return created