"""Uploading a product image: what's accepted, what's rejected, what's stored."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from app.core.config import get_settings
from tests.catalogue.factories import PRODUCTS


def _png(width: int = 40, height: int = 40) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (30, 75, 124)).save(buffer, format="PNG")
    return buffer.getvalue()


def upload_url(product_id) -> str:
    return f"{PRODUCTS}/{product_id}/images/upload"


@pytest.fixture(autouse=True)
def _clean_uploads():
    yield
    root = Path(get_settings().storage_local_path)
    for path in root.rglob("*"):
        if path.is_file():
            path.unlink()


async def test_an_uploaded_image_is_stored_and_attached(client, admin_headers, product):
    response = await client.post(
        upload_url(product["id"]),
        files={"file": ("shoe.png", _png(), "image/png")},
        data={"alt_text": "Navy trainer", "is_primary": "true"},
        headers=admin_headers,
    )

    assert response.status_code == 201, response.text
    image = response.json()["data"]
    assert image["alt_text"] == "Navy trainer"
    assert image["is_primary"] is True
    assert image["url"].startswith(get_settings().storage_public_base_url)

    stored = Path(get_settings().storage_local_path) / image["url"].split("/media/")[-1]
    assert stored.is_file()
    assert stored.stat().st_size > 0


async def test_files_are_partitioned_by_tenant(client, admin_headers, product, tenant):
    response = await client.post(
        upload_url(product["id"]),
        files={"file": ("shoe.png", _png(), "image/png")},
        headers=admin_headers,
    )

    assert response.status_code == 201, response.text
    assert str(tenant.id) in response.json()["data"]["url"]


async def test_a_pdf_pretending_to_be_an_image_is_refused(
    client, admin_headers, product
):
    response = await client.post(
        upload_url(product["id"]),
        files={"file": ("invoice.pdf", b"%PDF-1.4 not an image", "application/pdf")},
        headers=admin_headers,
    )

    assert response.status_code == 400, response.text
    assert "JPEG" in response.json()["message"]


async def test_a_declared_image_that_is_not_one_is_refused(
    client, admin_headers, product
):
    response = await client.post(
        upload_url(product["id"]),
        files={"file": ("fake.png", b"this is not a PNG", "image/png")},
        headers=admin_headers,
    )

    assert response.status_code == 400, response.text


async def test_an_oversized_upload_is_refused(client, admin_headers, product, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "max_upload_bytes", 100, raising=False)

    response = await client.post(
        upload_url(product["id"]),
        files={"file": ("big.png", _png(600, 600), "image/png")},
        headers=admin_headers,
    )

    assert response.status_code == 400, response.text
    assert "MB or smaller" in response.json()["message"]


async def test_a_large_image_is_scaled_down(client, admin_headers, product, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "image_max_dimension", 100, raising=False)

    response = await client.post(
        upload_url(product["id"]),
        files={"file": ("wide.png", _png(400, 200), "image/png")},
        headers=admin_headers,
    )

    assert response.status_code == 201, response.text
    stored = (
        Path(settings.storage_local_path)
        / response.json()["data"]["url"].split("/media/")[-1]
    )
    with Image.open(stored) as saved:
        assert max(saved.size) == 100
        assert saved.size == (100, 50)


async def test_uploading_requires_an_admin(client, customer_headers, product):
    response = await client.post(
        upload_url(product["id"]),
        files={"file": ("shoe.png", _png(), "image/png")},
        headers=customer_headers,
    )

    assert response.status_code == 403
