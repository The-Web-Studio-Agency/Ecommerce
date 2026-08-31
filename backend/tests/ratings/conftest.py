"""
Fixtures for the ratings and reviews tests.
"""

from __future__ import annotations

import pytest
import pytest_asyncio

from tests.catalogue.factories import make_category, make_product
from tests.conftest import headers_for
from tests.helpers import load_data, sample

DATA = load_data(__file__)

REVIEWS = DATA["routes"]["reviews"]
CUSTOMERS = DATA["customers"]


@pytest_asyncio.fixture(loop_scope="session")
async def customer(make_user, tenant):
    return await make_user(tenant=tenant, phone=CUSTOMERS["owner"])


@pytest.fixture
def customer_auth(customer) -> dict[str, str]:
    return headers_for(customer)


@pytest_asyncio.fixture(loop_scope="session")
async def reviewed_product(client, admin_headers):
    """Creates a product that can be used for reviews."""
    category = await make_category(client, admin_headers)
    product = await make_product(
        client,
        admin_headers,
        category["id"],
        name="Reviewable Product",
    )
    return product


@pytest.fixture
def review_payload():
    return sample(DATA, "review")