"""Testing global search, attribute filtering, sorting, validation, and lifecycle rules."""

from __future__ import annotations

from tests.search_filter.conftest import SEARCH


async def test_global_search_returns_matching_products(client, search_auth, search_test_catalogue):
    response = await client.get(SEARCH, params={"q": "Running"}, headers=search_auth)

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert len(body) == 1
    assert "Running" in body[0]["name"]


async def test_global_search_by_brand(client, search_auth, search_test_catalogue):
    response = await client.get(SEARCH, params={"q": "Puma"}, headers=search_auth)

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert len(body) == 1
    assert body[0]["brand"] == "Puma"


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


async def test_sorting_products_by_price_ascending(client, search_auth, search_test_catalogue):
    response = await client.get(SEARCH, params={"sort": "price"}, headers=search_auth)

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    prices = [float(item["price"]) for item in body]
    assert prices == sorted(prices)


async def test_price_range_validation_error(client, search_auth, search_test_catalogue):
    response = await client.get(SEARCH, params={"min_price": "1000.00", "max_price": "500.00"}, headers=search_auth)
    assert response.status_code == 400


async def test_negative_price_validation_error(client, search_auth, search_test_catalogue):
    response = await client.get(SEARCH, params={"min_price": "-10.00"}, headers=search_auth)
    assert response.status_code == 422


async def test_rating_filter_validation_error(client, search_auth, search_test_catalogue):
    response = await client.get(SEARCH, params={"min_rating": "6.0"}, headers=search_auth)
    assert response.status_code == 422


async def test_pagination_validation_errors(client, search_auth, search_test_catalogue):
    response = await client.get(SEARCH, params={"page": 0}, headers=search_auth)
    assert response.status_code == 422

    response = await client.get(SEARCH, params={"size": 150}, headers=search_auth)
    assert response.status_code == 422


async def test_autocomplete_suggestions_endpoint(client, search_auth, search_test_catalogue):
    response = await client.get("/api/v1/storefront/search-suggestions", params={"q": "Run"}, headers=search_auth)

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert len(body) >= 1
    assert any("Running" in suggestion["title"] for suggestion in body)


# ----------------------------- attribute filters -----------------------------


async def test_gender_filter_returns_only_matching_products(client, search_auth, search_test_catalogue):
    response = await client.get(SEARCH, params={"gender": "WOMEN"}, headers=search_auth)

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert len(body) == 1
    assert body[0]["name"] == "Cotton T-Shirt"
    assert body[0]["gender"] == "WOMEN"


async def test_gender_filter_excludes_non_matching_products(client, search_auth, search_test_catalogue):
    response = await client.get(SEARCH, params={"gender": "UNISEX"}, headers=search_auth)

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert len(body) == 1
    assert body[0]["name"] == "Formal Shirt"
    assert body[0]["gender"] == "UNISEX"


async def test_color_filter_does_not_500_and_filters_correctly(client, search_auth, search_test_catalogue):
    response = await client.get(SEARCH, params={"color": "Black"}, headers=search_auth)

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert len(body) == 1
    assert body[0]["name"] == "Running Sneaker"


async def test_size_filter_uses_its_own_query_param(client, search_auth, search_test_catalogue):
    response = await client.get(SEARCH, params={"product_size": "L"}, headers=search_auth)

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert len(body) == 1
    assert body[0]["name"] == "Formal Shirt"


async def test_brand_filter_is_case_insensitive(client, search_auth, search_test_catalogue):
    response = await client.get(SEARCH, params={"brand": "nike"}, headers=search_auth)

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert len(body) == 1
    assert body[0]["brand"] == "Nike"


async def test_gender_color_size_filters_are_case_insensitive(client, search_auth, search_test_catalogue):
    response = await client.get(SEARCH, params={"gender": "women"}, headers=search_auth)
    assert response.status_code == 200, response.text
    assert len(response.json()["data"]) == 1
    assert response.json()["data"][0]["name"] == "Cotton T-Shirt"

    response = await client.get(SEARCH, params={"color": "black"}, headers=search_auth)
    assert response.status_code == 200, response.text
    assert len(response.json()["data"]) == 1
    assert response.json()["data"][0]["name"] == "Running Sneaker"


async def test_gender_filter_excludes_products_without_a_gender(
    client, search_auth, search_multi_variant_product
):
    """search_multi_variant_product's "Graphic Hoodie" has no gender set --
    it must never match a gender filter, only appear when gender is omitted."""
    response = await client.get(SEARCH, params={"gender": "MEN"}, headers=search_auth)
    assert response.status_code == 200, response.text
    assert all(item["name"] != "Graphic Hoodie" for item in response.json()["data"])

    response = await client.get(SEARCH, params={"q": "Graphic Hoodie"}, headers=search_auth)
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert len(body) == 1
    assert body[0]["gender"] is None


# -------------------------------- rating filter -------------------------------


async def test_rating_filter_matches_and_exposes_average_rating(
    client, search_auth, search_ratings_and_orders
):
    response = await client.get(SEARCH, params={"min_rating": "3.5"}, headers=search_auth)

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert len(body) == 1
    assert body[0]["name"] == "Cotton T-Shirt"
    assert body[0]["rating"] == 4.0


async def test_rating_filter_excludes_unrated_and_low_rated_products(
    client, search_auth, search_ratings_and_orders
):
    response = await client.get(SEARCH, params={"min_rating": "1", "max_rating": "2.5"}, headers=search_auth)

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert len(body) == 1
    assert body[0]["name"] == "Formal Shirt"
    assert body[0]["rating"] == 2.0


async def test_unrated_product_exposes_null_rating(client, search_auth, search_ratings_and_orders):
    response = await client.get(SEARCH, params={"q": "Running Sneaker"}, headers=search_auth)

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert len(body) == 1
    assert body[0]["rating"] is None


# ---------------------------------- sorting -----------------------------------


async def test_invalid_sort_parameter_is_rejected(client, search_auth, search_test_catalogue):
    response = await client.get(SEARCH, params={"sort": "bogus"}, headers=search_auth)
    assert response.status_code == 422


async def test_recommended_sort_is_based_on_popularity(client, search_auth, search_ratings_and_orders):
    # Default sort (RECOMMENDED): Cotton T-Shirt (5 units) outsells Formal
    # Shirt (2 units) outsells Running Sneaker (0 -- its only order was
    # cancelled and must not count).
    response = await client.get(SEARCH, headers=search_auth)

    assert response.status_code == 200, response.text
    names = [item["name"] for item in response.json()["data"]]
    assert names.index("Cotton T-Shirt") < names.index("Formal Shirt") < names.index("Running Sneaker")


# --------------------------------- pagination ---------------------------------


async def test_custom_page_size_does_not_500(client, search_auth, search_test_catalogue):
    response = await client.get(SEARCH, params={"size": 2}, headers=search_auth)

    assert response.status_code == 200, response.text
    assert len(response.json()["data"]) <= 2
    assert response.json()["meta"]["page_size"] == 2


async def test_page_size_boundaries_are_enforced(client, search_auth, search_test_catalogue):
    at_max = await client.get(SEARCH, params={"size": 100}, headers=search_auth)
    assert at_max.status_code == 200, at_max.text

    at_min = await client.get(SEARCH, params={"size": 1}, headers=search_auth)
    assert at_min.status_code == 200, at_min.text
    assert len(at_min.json()["data"]) <= 1

    over_max = await client.get(SEARCH, params={"size": 101}, headers=search_auth)
    assert over_max.status_code == 422

    under_min = await client.get(SEARCH, params={"size": 0}, headers=search_auth)
    assert under_min.status_code == 422


# ------------------------------ combined parameters ----------------------------


async def test_combined_search_filters_sort_and_pagination(client, search_auth, search_ratings_and_orders):
    response = await client.get(
        SEARCH,
        params={
            "q": "Shirt",
            "gender": "UNISEX",
            "color": "Blue",
            "product_size": "L",
            "min_price": "500",
            "max_price": "1500",
            "min_rating": "1",
            "sort": "-price",
            "page": 1,
            "size": 10,
        },
        headers=search_auth,
    )

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert len(body) == 1
    assert body[0]["name"] == "Formal Shirt"


# -------------------------------- search history --------------------------------


async def test_search_history_records_and_returns_recent_searches(
    client, search_auth, search_test_catalogue
):
    await client.get(SEARCH, params={"q": "Running"}, headers=search_auth)
    await client.get(SEARCH, params={"q": "Puma"}, headers=search_auth)

    response = await client.get("/api/v1/storefront/search-history", headers=search_auth)

    assert response.status_code == 200, response.text
    history = response.json()["data"]
    assert "Running" in history
    assert "Puma" in history
    # Most recent search first.
    assert history.index("Puma") < history.index("Running")


async def test_search_history_requires_authentication(client, search_test_catalogue):
    response = await client.get("/api/v1/storefront/search-history")
    assert response.status_code == 401


# ----------------------------- variant attributes -----------------------------


async def test_response_exposes_actual_variant_color_and_size_combinations(
    client, search_auth, search_multi_variant_product
):
    response = await client.get(SEARCH, params={"q": "Graphic Hoodie"}, headers=search_auth)

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert len(body) == 1

    variants = body[0]["variants"]
    assert len(variants) == 3

    combos = {(v["options"]["Color"], v["options"]["Size"]) for v in variants}
    assert combos == {("Black", "S"), ("Black", "M"), ("Green", "S")}

    # Every variant carries its own id, not a shared/aggregated one.
    assert len({v["variant_id"] for v in variants}) == 3


async def test_variant_attributes_reflect_the_filtered_matching_variant(
    client, search_auth, search_test_catalogue
):
    """Preserves existing color-filter behavior: a product matches when ANY
    of its variants has the requested color, and the response still shows
    that variant's real options -- never inferred from name/brand/etc."""
    response = await client.get(SEARCH, params={"color": "Black"}, headers=search_auth)

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert len(body) == 1
    assert body[0]["name"] == "Running Sneaker"

    assert body[0]["gender"] == "MEN"

    variants = body[0]["variants"]
    assert len(variants) == 1
    assert variants[0]["options"] == {"Color": "Black", "Size": "M"}


async def test_single_variant_product_exposes_one_variant_entry(
    client, search_auth, search_test_catalogue
):
    response = await client.get(SEARCH, params={"q": "Cotton T-Shirt"}, headers=search_auth)

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert len(body) == 1
    assert len(body[0]["variants"]) == 1
    assert body[0]["variants"][0]["options"]["Color"] == "White"
    assert body[0]["variants"][0]["options"]["Size"] == "S"