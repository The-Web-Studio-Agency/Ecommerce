"""
Builders and fixture data shared across test packages.

These live here rather than in a test module so that, say, the cart tests can
create a product without importing from the catalogue test suite.

The default payloads come from tests/data/*.json, so adjusting the sample data
does not mean editing Python. Every builder deep-copies what it loads, so a
test passing overrides can never mutate the shared defaults for the next test.
"""

from __future__ import annotations

import copy
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent / "data"

CATEGORIES = "/api/v1/catalogue/categories"
PRODUCTS = "/api/v1/catalogue/products"
VARIANTS = "/api/v1/catalogue/variants"


@lru_cache
def _load(name: str) -> dict[str, Any]:
    """Read a JSON fixture file once and cache it."""
    return json.loads((DATA_DIR / f"{name}.json").read_text())


def sample(file: str, key: str, /, **overrides: Any) -> dict[str, Any]:
    """
    A fresh copy of one payload from a JSON fixture, with overrides applied.

    Copied rather than shared, so `sample("catalogue", "product", name="X")`
    never leaks that name into the next test.

    `file` and `key` are positional-only so that "name" and "key" stay usable
    as payload override keys.
    """
    payload = copy.deepcopy(_load(file)[key])
    payload.update(overrides)
    return payload


# Read straight from the JSON so a test can drop it into an images list.
IMAGE = _load("catalogue")["image"]


async def make_category(client, headers, **overrides) -> dict:
    payload = sample("catalogue", "category", **overrides)
    response = await client.post(CATEGORIES, json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def make_product(client, headers, category_id, **overrides) -> dict:
    payload = sample("catalogue", "product", category_id=category_id, **overrides)
    payload.setdefault("images", [copy.deepcopy(IMAGE)])
    response = await client.post(PRODUCTS, json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def make_variant(client, headers, product_id, **overrides) -> dict:
    payload = sample("catalogue", "variant", **overrides)
    response = await client.post(
        f"{PRODUCTS}/{product_id}/variants", json=payload, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]
