"""Testing global search, attribute filtering, and sorting functionality."""

from __future__ import annotations

from tests.search_filter.conftest import SEARCH


async def test_global_search_returns_matching_products(client, search_auth, search_test_catalogue):
    response = await client.get(SEARCH, params={"q": "Running"}, headers=search_auth)

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert len(body) == 1
    assert "Running" in body[0]["name"]


async def test_search_with_no_matches_returns_empty_list(client, search_auth, search_test_catalogue):
    response = await client.get(SEARCH, params={"q": "NonExistentItem999"}, headers=search_auth)

    assert response.status_code == 200, response.text
    assert response.json()["data"] == []


async def test_filtering_products_by_price_range(client, search_auth, search_test_catalogue):
    response = await client.get(SEARCH, params={"min_price": "400.00", "max_price": "600.00"}, headers=search_auth)

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert len(body) == 1
    assert body[0]["price"] == "499.00"


async def test_sorting_products_by_price_descending(client, search_auth, search_test_catalogue):
    response = await client.get(SEARCH, params={"sort": "-price"}, headers=search_auth)

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    prices = [float(item["price"]) for item in body]
    assert prices == sorted(prices, reverse=True)


async def test_autocomplete_suggestions_endpoint(client, search_auth, search_test_catalogue):
    response = await client.get("/api/v1/storefront/search-suggestions", params={"q": "Run"}, headers=search_auth)

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert len(body) >= 1
    assert any("Running" in suggestion["title"] for suggestion in body)