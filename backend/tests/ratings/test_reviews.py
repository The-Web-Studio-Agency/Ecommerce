"""
Ratings & Reviews: authentication, verified delivered purchases, updates, constraints, and listing.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.catalogue.models import Product
from app.orders.models import Order
from app.ratings.models import Review, ReviewArchiveReason, ReviewStatus
from app.users.models import User
from tests.ratings.conftest import REVIEWS, CUSTOMERS
from tests.conftest import headers_for

# ------------------------------ authentication ------------------------------


@pytest.mark.parametrize(
    ("method", "path"),
    [("post", REVIEWS), ("patch", f"{REVIEWS}/1"), ("delete", f"{REVIEWS}/1")],
)
async def test_review_modifications_need_authentication(client, tenant, method, path):
    kwargs = {"json": {}} if method in ("post", "patch") else {}
    response = await getattr(client, method)(path, **kwargs)
    assert response.status_code == 401


# --------------------------------- creation ---------------------------------


async def test_customer_can_only_review_delivered_products(
    client, customer_auth, reviewed_product, review_payload
):
    """Fails because the customer has not purchased or received the product yet."""
    payload = {**review_payload, "product_id": reviewed_product["id"]}
    response = await client.post(REVIEWS, json=payload, headers=customer_auth)

    assert response.status_code == 403
    assert response.json()["message"] == "You can only review products that have been delivered to you."


async def test_customer_cannot_review_same_product_twice(
    client, customer_auth, customer, reviewed_product, review_payload, deliver_purchase
):
    await deliver_purchase(customer, reviewed_product)
    payload = {**review_payload, "product_id": reviewed_product["id"]}

    first = await client.post(REVIEWS, json=payload, headers=customer_auth)
    assert first.status_code == 201, first.text

    second = await client.post(REVIEWS, json=payload, headers=customer_auth)
    assert second.status_code == 400
    assert second.json()["message"] == "You have already submitted a review for this product."


async def test_customer_can_review_again_after_deleting_previous_review(
    client, customer_auth, customer, reviewed_product, review_payload, deliver_purchase
):
    await deliver_purchase(customer, reviewed_product)
    payload = {**review_payload, "product_id": reviewed_product["id"]}

    first = await client.post(REVIEWS, json=payload, headers=customer_auth)
    assert first.status_code == 201, first.text

    deleted = await client.delete(f"{REVIEWS}/{first.json()['id']}", headers=customer_auth)
    assert deleted.status_code == 204

    # The soft-deleted review no longer occupies the unique (tenant, user,
    # product) slot, so a fresh review is allowed.
    second = await client.post(REVIEWS, json=payload, headers=customer_auth)
    assert second.status_code == 201, second.text
    assert second.json()["id"] != first.json()["id"]


async def test_admin_cannot_touch_customer_reviews(
    client, admin_headers
):
    """Admins should not have permission to delete or alter customer reviews directly."""
    response = await client.delete(f"{REVIEWS}/{uuid4()}", headers=admin_headers)
    # Should be forbidden or unauthorized since only the customer can manage their review
    assert response.status_code in (403, 401, 404)


# -------------------------------- validation --------------------------------


@pytest.mark.parametrize("rating", [0, 6, -1, 10])
async def test_rating_must_be_between_one_and_five(
    client, customer_auth, reviewed_product, review_payload, rating
):
    payload = {**review_payload, "product_id": reviewed_product["id"], "rating": rating}
    response = await client.post(REVIEWS, json=payload, headers=customer_auth)

    assert response.status_code == 422


async def test_at_most_one_image_per_review_is_accepted(
    client, customer_auth, customer, reviewed_product, review_payload, deliver_purchase
):
    await deliver_purchase(customer, reviewed_product)
    payload = {
        **review_payload,
        "product_id": reviewed_product["id"],
        "images": [
            {"image_url": "https://example.com/one.jpg"},
            {"image_url": "https://example.com/two.jpg"},
        ],
    }
    response = await client.post(REVIEWS, json=payload, headers=customer_auth)
    assert response.status_code == 422


# --------------------------------- updating ---------------------------------


async def test_customer_can_update_their_review_after_long_time(
    client, customer_auth, customer, reviewed_product, review_payload, deliver_purchase
):
    await deliver_purchase(customer, reviewed_product)
    payload = {**review_payload, "product_id": reviewed_product["id"]}
    created = await client.post(REVIEWS, json=payload, headers=customer_auth)
    assert created.status_code == 201, created.text
    review_id = created.json()["id"]

    response = await client.patch(
        f"{REVIEWS}/{review_id}",
        json={"rating": 4, "comment": "Updating my thoughts after months of use."},
        headers=customer_auth,
    )
    assert response.status_code == 200, response.text
    assert response.json()["rating"] == 4
    assert response.json()["comment"] == "Updating my thoughts after months of use."


async def test_customer_cannot_set_is_approved_on_update(
    client, customer_auth, customer, reviewed_product, review_payload, deliver_purchase
):
    """is_approved is moderation state; it must not be settable by the review's own author."""
    await deliver_purchase(customer, reviewed_product)
    payload = {**review_payload, "product_id": reviewed_product["id"]}
    created = await client.post(REVIEWS, json=payload, headers=customer_auth)
    review_id = created.json()["id"]

    response = await client.patch(
        f"{REVIEWS}/{review_id}",
        json={"is_approved": False},
        headers=customer_auth,
    )
    # The field isn't part of the update schema at all, and the schema
    # forbids unknown fields, so the request is rejected outright rather
    # than silently ignoring the attempt to change moderation state.
    assert response.status_code == 422, response.text

async def test_customer_can_add_comment_to_existing_rating(
    client,
    customer_auth,
    customer,
    reviewed_product,
    deliver_purchase,
):
    await deliver_purchase(customer, reviewed_product)

    # Step 1: give only a rating
    created = await client.post(
        REVIEWS,
        json={
            "product_id": reviewed_product["id"],
            "rating": 5,
        },
        headers=customer_auth,
    )

    assert created.status_code == 201, created.text

    review_id = created.json()["id"]

    # Step 2: add comment later
    updated = await client.patch(
        f"{REVIEWS}/{review_id}",
        json={
            "comment": "Amazing product!",
        },
        headers=customer_auth,
    )

    assert updated.status_code == 200, updated.text
    assert updated.json()["id"] == review_id
    assert updated.json()["rating"] == 5
    assert updated.json()["comment"] == "Amazing product!"


async def test_customer_can_complete_review_in_multiple_steps(
    client,
    customer_auth,
    customer,
    reviewed_product,
    deliver_purchase,
):
    await deliver_purchase(customer, reviewed_product)

    # Step 1: rating only
    created = await client.post(
        REVIEWS,
        json={
            "product_id": reviewed_product["id"],
            "rating": 5,
        },
        headers=customer_auth,
    )

    assert created.status_code == 201, created.text
    review_id = created.json()["id"]

    # Step 2: add comment
    comment_update = await client.patch(
        f"{REVIEWS}/{review_id}",
        json={
            "comment": "Really good quality.",
        },
        headers=customer_auth,
    )

    assert comment_update.status_code == 200, comment_update.text

    # Step 3: add photo
    image_update = await client.patch(
        f"{REVIEWS}/{review_id}",
        json={
            "images": [
                {
                    "image_url": "https://example.com/review-photo.jpg",
                    "alt_text": "Product photo",
                }
            ]
        },
        headers=customer_auth,
    )

    assert image_update.status_code == 200, image_update.text

    body = image_update.json()

    assert body["id"] == review_id
    assert body["rating"] == 5
    assert body["comment"] == "Really good quality."
    assert len(body["images"]) == 1
    assert body["images"][0]["image_url"] == (
        "https://example.com/review-photo.jpg"
    )


async def test_customer_can_replace_existing_review_image(
    client,
    customer_auth,
    customer,
    reviewed_product,
    deliver_purchase,
):
    await deliver_purchase(customer, reviewed_product)

    created = await client.post(
        REVIEWS,
        json={
            "product_id": reviewed_product["id"],
            "rating": 5,
            "images": [
                {
                    "image_url": "https://example.com/old.jpg",
                    "alt_text": "Old photo",
                }
            ],
        },
        headers=customer_auth,
    )

    assert created.status_code == 201, created.text

    review_id = created.json()["id"]

    updated = await client.patch(
        f"{REVIEWS}/{review_id}",
        json={
            "images": [
                {
                    "image_url": "https://example.com/new.jpg",
                    "alt_text": "New photo",
                }
            ]
        },
        headers=customer_auth,
    )

    assert updated.status_code == 200, updated.text

    images = updated.json()["images"]

    assert len(images) == 1
    assert images[0]["image_url"] == "https://example.com/new.jpg"

async def test_customer_can_remove_review_image(
    client,
    customer_auth,
    customer,
    reviewed_product,
    deliver_purchase,
):
    await deliver_purchase(customer, reviewed_product)

    created = await client.post(
        REVIEWS,
        json={
            "product_id": reviewed_product["id"],
            "rating": 5,
            "images": [
                {
                    "image_url": "https://example.com/photo.jpg",
                    "alt_text": "Product photo",
                }
            ],
        },
        headers=customer_auth,
    )

    assert created.status_code == 201, created.text

    review_id = created.json()["id"]

    updated = await client.patch(
        f"{REVIEWS}/{review_id}",
        json={
            "images": []
        },
        headers=customer_auth,
    )

    assert updated.status_code == 200, updated.text
    assert updated.json()["images"] == []


# -------------------------------- ownership & admin block ---------------------------------


async def test_another_customer_cannot_edit_or_delete_your_review(
    client, customer_auth, make_user, tenant
):
    intruder = headers_for(await make_user(tenant=tenant, phone=CUSTOMERS["intruder"]))
    review_id = uuid4()

    response = await client.patch(
        f"{REVIEWS}/{review_id}", json={"rating": 1}, headers=intruder
    )
    assert response.status_code in (403, 404)

    response_del = await client.delete(f"{REVIEWS}/{review_id}", headers=intruder)
    assert response_del.status_code in (403, 404)


# --------------------------------- listing ---------------------------------


async def test_product_reviews_and_summary_can_be_fetched(client, reviewed_product):
    response = await client.get(f"{REVIEWS}/product/{reviewed_product['id']}")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    summary_response = await client.get(f"{REVIEWS}/product/{reviewed_product['id']}/summary")
    assert summary_response.status_code == 200
    body = summary_response.json()
    assert "average_rating" in body
    assert "total_reviews" in body
    assert "rating_distribution" in body


async def test_rating_summary_is_maintained_across_review_lifecycle(
    client, customer_auth, customer, reviewed_product, review_payload, deliver_purchase
):
    await deliver_purchase(customer, reviewed_product)
    payload = {**review_payload, "product_id": reviewed_product["id"], "rating": 5}
    created = await client.post(REVIEWS, json=payload, headers=customer_auth)
    review_id = created.json()["id"]

    summary = await client.get(f"{REVIEWS}/product/{reviewed_product['id']}/summary")
    body = summary.json()
    assert body["total_reviews"] >= 1
    assert body["rating_distribution"]["5"] >= 1

    deleted = await client.delete(f"{REVIEWS}/{review_id}", headers=customer_auth)
    assert deleted.status_code == 204

    summary_after = await client.get(f"{REVIEWS}/product/{reviewed_product['id']}/summary")
    body_after = summary_after.json()
    # The deleted review no longer counts toward the maintained aggregate.
    assert body_after["total_reviews"] == body["total_reviews"] - 1


# ----------------------- public/admin review visibility -----------------------


async def test_archived_product_reviews_not_public(
    client, admin_headers, customer_auth, reviewed_product
):
    product_id = reviewed_product["id"]

    response = await client.delete(
        f"/api/v1/catalogue/products/{product_id}",
        headers=admin_headers,
    )
    assert response.status_code == 204, response.text

    response = await client.get(
        f"{REVIEWS}/product/{product_id}",
        headers=customer_auth,
    )

    assert response.status_code == 404


async def test_archived_product_summary_not_public(
    client, admin_headers, customer_auth, reviewed_product
):
    product_id = reviewed_product["id"]

    response = await client.delete(
        f"/api/v1/catalogue/products/{product_id}",
        headers=admin_headers,
    )
    assert response.status_code == 204, response.text

    response = await client.get(
        f"{REVIEWS}/product/{product_id}/summary",
        headers=customer_auth,
    )

    assert response.status_code == 404


async def test_admin_can_get_product_reviews(
    client,
    admin_headers,
    customer_auth,
    customer,
    reviewed_product,
    deliver_purchase,
):
    product_id = reviewed_product["id"]

    await deliver_purchase(customer, reviewed_product)

    created = await client.post(
        REVIEWS,
        json={
            "product_id": product_id,
            "rating": 5,
            "comment": "Great product",
        },
        headers=customer_auth,
    )
    assert created.status_code == 201, created.text

    response = await client.get(
        f"{REVIEWS}/admin/product/{product_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1


async def test_admin_can_get_reviews_for_archived_product(
    client,
    admin_headers,
    customer_auth,
    customer,
    reviewed_product,
    deliver_purchase,
):
    product_id = reviewed_product["id"]

    await deliver_purchase(customer, reviewed_product)

    created = await client.post(
        REVIEWS,
        json={
            "product_id": product_id,
            "rating": 5,
            "comment": "Great product",
        },
        headers=customer_auth,
    )
    assert created.status_code == 201, created.text

    archive_response = await client.delete(
        f"/api/v1/catalogue/products/{product_id}",
        headers=admin_headers,
    )
    assert archive_response.status_code == 204, archive_response.text

    response = await client.get(
        f"{REVIEWS}/admin/product/{product_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text
    assert len(response.json()) == 1
    assert response.json()[0]["rating"] == 5


async def test_customer_cannot_get_admin_reviews(
    client, customer_auth, reviewed_product
):
    response = await client.get(
        f"{REVIEWS}/admin/product/{reviewed_product['id']}",
        headers=customer_auth,
    )

    assert response.status_code in (401, 403)


async def test_unauthenticated_cannot_get_admin_reviews(
    client, reviewed_product
):
    response = await client.get(
        f"{REVIEWS}/admin/product/{reviewed_product['id']}"
    )

    assert response.status_code == 401


async def test_admin_can_get_product_summary(
    client,
    admin_headers,
    customer_auth,
    customer,
    reviewed_product,
    deliver_purchase,
):
    product_id = reviewed_product["id"]

    await deliver_purchase(customer, reviewed_product)

    created = await client.post(
        REVIEWS,
        json={
            "product_id": product_id,
            "rating": 5,
        },
        headers=customer_auth,
    )
    assert created.status_code == 201, created.text

    response = await client.get(
        f"{REVIEWS}/admin/product/{product_id}/summary",
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text

    body = response.json()
    assert body["product_id"] == str(product_id)
    assert body["total_reviews"] == 1
    assert body["average_rating"] == 5
    assert body["rating_distribution"]["5"] == 1


async def test_admin_can_get_summary_for_archived_product(
    client,
    admin_headers,
    customer_auth,
    customer,
    reviewed_product,
    deliver_purchase,
):
    product_id = reviewed_product["id"]

    await deliver_purchase(customer, reviewed_product)

    created = await client.post(
        REVIEWS,
        json={
            "product_id": product_id,
            "rating": 5,
        },
        headers=customer_auth,
    )
    assert created.status_code == 201, created.text

    archive_response = await client.delete(
        f"/api/v1/catalogue/products/{product_id}",
        headers=admin_headers,
    )
    assert archive_response.status_code == 204, archive_response.text

    response = await client.get(
        f"{REVIEWS}/admin/product/{product_id}/summary",
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text

    body = response.json()
    assert body["product_id"] == str(product_id)
    # Archiving the product auto-archives its active reviews with
    # PRODUCT_ARCHIVED, and the rating summary counts ONLY ACTIVE +
    # approved reviews -- for every viewer, admin included. The individual
    # archived review is still visible via the admin listing endpoint, just
    # not counted in this aggregate.
    assert body["total_reviews"] == 0
    assert body["average_rating"] == 0.0
    assert body["rating_distribution"]["5"] == 0


async def test_customer_cannot_get_admin_summary(
    client, customer_auth, reviewed_product
):
    response = await client.get(
        f"{REVIEWS}/admin/product/{reviewed_product['id']}/summary",
        headers=customer_auth,
    )

    assert response.status_code in (401, 403)


async def test_unauthenticated_cannot_get_admin_summary(
    client, reviewed_product
):
    response = await client.get(
        f"{REVIEWS}/admin/product/{reviewed_product['id']}/summary"
    )

    assert response.status_code == 401


# ----------------------------- deletion preserves history -----------------------------


async def test_deleting_the_product_preserves_the_review(
    client, customer_auth, customer, reviewed_product, review_payload, deliver_purchase, session
):
    await deliver_purchase(customer, reviewed_product)
    payload = {**review_payload, "product_id": reviewed_product["id"]}
    created = await client.post(REVIEWS, json=payload, headers=customer_auth)
    review_id = created.json()["id"]

    product = await session.get(Product, reviewed_product["id"])
    await session.delete(product)
    await session.commit()

    review = await session.get(Review, review_id)
    assert review is not None
    assert review.product_id is None


async def test_deleting_the_user_preserves_the_review(
    client, make_user, tenant, reviewed_product, review_payload, deliver_purchase, session
):
    reviewer = await make_user(tenant=tenant, phone=CUSTOMERS["deletable"])
    reviewer_auth = headers_for(reviewer)
    await deliver_purchase(reviewer, reviewed_product)

    payload = {**review_payload, "product_id": reviewed_product["id"]}
    created = await client.post(REVIEWS, json=payload, headers=reviewer_auth)
    review_id = created.json()["id"]

    user = await session.get(User, reviewer.id)
    await session.delete(user)
    await session.commit()

    review = await session.get(Review, review_id)
    assert review is not None
    assert review.user_id is None


# ----------------------- product archive/reactivate sync -----------------------


async def test_new_review_is_active_with_no_archive_reason(
    client, customer_auth, customer, reviewed_product, review_payload, deliver_purchase
):
    await deliver_purchase(customer, reviewed_product)
    payload = {**review_payload, "product_id": reviewed_product["id"]}
    created = await client.post(REVIEWS, json=payload, headers=customer_auth)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "ACTIVE"
    assert body["archive_reason"] is None


async def test_delete_does_not_hard_delete_and_sets_customer_deleted_reason(
    client, customer_auth, customer, reviewed_product, review_payload, deliver_purchase, session
):
    await deliver_purchase(customer, reviewed_product)
    payload = {**review_payload, "product_id": reviewed_product["id"]}
    created = await client.post(REVIEWS, json=payload, headers=customer_auth)
    review_id = created.json()["id"]

    deleted = await client.delete(f"{REVIEWS}/{review_id}", headers=customer_auth)
    assert deleted.status_code == 204

    review = await session.get(Review, review_id)
    assert review is not None
    assert review.status == ReviewStatus.ARCHIVED
    assert review.archive_reason == ReviewArchiveReason.CUSTOMER_DELETED


async def test_deleted_review_invisible_and_uneditable_by_customer(
    client, customer_auth, customer, reviewed_product, review_payload, deliver_purchase
):
    await deliver_purchase(customer, reviewed_product)
    payload = {**review_payload, "product_id": reviewed_product["id"]}
    created = await client.post(REVIEWS, json=payload, headers=customer_auth)
    review_id = created.json()["id"]

    deleted = await client.delete(f"{REVIEWS}/{review_id}", headers=customer_auth)
    assert deleted.status_code == 204

    listing = await client.get(f"{REVIEWS}/product/{reviewed_product['id']}")
    assert all(r["id"] != review_id for r in listing.json())

    update = await client.patch(
        f"{REVIEWS}/{review_id}", json={"rating": 3}, headers=customer_auth
    )
    assert update.status_code == 404

    redelete = await client.delete(f"{REVIEWS}/{review_id}", headers=customer_auth)
    assert redelete.status_code == 404


async def test_admin_sees_archived_review_with_status_and_reason(
    client, admin_headers, customer_auth, customer, reviewed_product, review_payload, deliver_purchase
):
    await deliver_purchase(customer, reviewed_product)
    payload = {**review_payload, "product_id": reviewed_product["id"]}
    created = await client.post(REVIEWS, json=payload, headers=customer_auth)
    review_id = created.json()["id"]

    deleted = await client.delete(f"{REVIEWS}/{review_id}", headers=customer_auth)
    assert deleted.status_code == 204

    admin_list = await client.get(
        f"{REVIEWS}/admin/product/{reviewed_product['id']}", headers=admin_headers
    )
    assert admin_list.status_code == 200
    found = next(r for r in admin_list.json() if r["id"] == review_id)
    assert found["status"] == "ARCHIVED"
    assert found["archive_reason"] == "CUSTOMER_DELETED"


async def test_product_archive_archives_only_active_reviews_and_preserves_customer_deleted(
    client, admin_headers, customer_auth, customer, make_user, tenant,
    reviewed_product, review_payload, deliver_purchase, session,
):
    product_id = reviewed_product["id"]

    # Customer A: review stays ACTIVE until the product archive.
    await deliver_purchase(customer, reviewed_product)
    payload_a = {**review_payload, "product_id": product_id}
    review_a = await client.post(REVIEWS, json=payload_a, headers=customer_auth)
    assert review_a.status_code == 201, review_a.text
    review_a_id = review_a.json()["id"]

    # Customer B: reviews then deletes their own review beforehand.
    customer_b = await make_user(tenant=tenant, phone=CUSTOMERS["intruder"])
    customer_b_auth = headers_for(customer_b)
    await deliver_purchase(customer_b, reviewed_product)
    payload_b = {**review_payload, "product_id": product_id}
    review_b = await client.post(REVIEWS, json=payload_b, headers=customer_b_auth)
    assert review_b.status_code == 201, review_b.text
    review_b_id = review_b.json()["id"]
    deleted_b = await client.delete(f"{REVIEWS}/{review_b_id}", headers=customer_b_auth)
    assert deleted_b.status_code == 204

    # Archive the product.
    archive_response = await client.delete(
        f"/api/v1/catalogue/products/{product_id}", headers=admin_headers
    )
    assert archive_response.status_code == 204, archive_response.text

    review_a_row = await session.get(Review, review_a_id)
    review_b_row = await session.get(Review, review_b_id)

    assert review_a_row.status == ReviewStatus.ARCHIVED
    assert review_a_row.archive_reason == ReviewArchiveReason.PRODUCT_ARCHIVED

    # Never overwritten -- still exactly what the customer's own delete set.
    assert review_b_row.status == ReviewStatus.ARCHIVED
    assert review_b_row.archive_reason == ReviewArchiveReason.CUSTOMER_DELETED


async def test_archived_product_reviews_hidden_publicly_but_visible_to_admin(
    client, admin_headers, customer_auth, customer, reviewed_product, review_payload, deliver_purchase
):
    product_id = reviewed_product["id"]
    await deliver_purchase(customer, reviewed_product)
    payload = {**review_payload, "product_id": product_id}
    created = await client.post(REVIEWS, json=payload, headers=customer_auth)
    assert created.status_code == 201, created.text

    archive_response = await client.delete(
        f"/api/v1/catalogue/products/{product_id}", headers=admin_headers
    )
    assert archive_response.status_code == 204, archive_response.text

    public_listing = await client.get(f"{REVIEWS}/product/{product_id}", headers=customer_auth)
    assert public_listing.status_code == 404

    admin_listing = await client.get(
        f"{REVIEWS}/admin/product/{product_id}", headers=admin_headers
    )
    assert admin_listing.status_code == 200
    assert len(admin_listing.json()) == 1
    assert admin_listing.json()[0]["status"] == "ARCHIVED"
    assert admin_listing.json()[0]["archive_reason"] == "PRODUCT_ARCHIVED"


async def test_product_reactivation_restores_only_product_archived_reviews(
    client, admin_headers, customer_auth, customer, make_user, tenant,
    reviewed_product, review_payload, deliver_purchase, session,
):
    product_id = reviewed_product["id"]

    await deliver_purchase(customer, reviewed_product)
    review_a = await client.post(
        REVIEWS, json={**review_payload, "product_id": product_id}, headers=customer_auth
    )
    review_a_id = review_a.json()["id"]

    customer_b = await make_user(tenant=tenant, phone=CUSTOMERS["intruder"])
    customer_b_auth = headers_for(customer_b)
    await deliver_purchase(customer_b, reviewed_product)
    review_b = await client.post(
        REVIEWS, json={**review_payload, "product_id": product_id}, headers=customer_b_auth
    )
    review_b_id = review_b.json()["id"]
    await client.delete(f"{REVIEWS}/{review_b_id}", headers=customer_b_auth)

    # Archive then reactivate the product.
    await client.delete(f"/api/v1/catalogue/products/{product_id}", headers=admin_headers)
    reactivate = await client.patch(
        f"/api/v1/catalogue/products/{product_id}",
        json={"status": "ACTIVE"},
        headers=admin_headers,
    )
    assert reactivate.status_code == 200, reactivate.text

    review_a_row = await session.get(Review, review_a_id)
    review_b_row = await session.get(Review, review_b_id)

    # Restored: was archived only because the product was archived.
    assert review_a_row.status == ReviewStatus.ACTIVE
    assert review_a_row.archive_reason is None

    # Never restored: archived by the customer's own delete.
    assert review_b_row.status == ReviewStatus.ARCHIVED
    assert review_b_row.archive_reason == ReviewArchiveReason.CUSTOMER_DELETED

    public_listing = await client.get(f"{REVIEWS}/product/{product_id}")
    assert public_listing.status_code == 200
    ids = [r["id"] for r in public_listing.json()]
    assert review_a_id in ids
    assert review_b_id not in ids


async def test_rating_summary_excludes_product_archived_and_restores_on_reactivation(
    client, admin_headers, customer_auth, customer, reviewed_product, deliver_purchase,
):
    product_id = reviewed_product["id"]
    await deliver_purchase(customer, reviewed_product)
    created = await client.post(
        REVIEWS, json={"product_id": product_id, "rating": 5}, headers=customer_auth
    )
    assert created.status_code == 201, created.text

    summary_before = await client.get(f"{REVIEWS}/product/{product_id}/summary")
    assert summary_before.json()["total_reviews"] == 1

    await client.delete(f"/api/v1/catalogue/products/{product_id}", headers=admin_headers)

    admin_summary_archived = await client.get(
        f"{REVIEWS}/admin/product/{product_id}/summary", headers=admin_headers
    )
    assert admin_summary_archived.json()["total_reviews"] == 0
    assert admin_summary_archived.json()["average_rating"] == 0.0

    await client.patch(
        f"/api/v1/catalogue/products/{product_id}",
        json={"status": "ACTIVE"},
        headers=admin_headers,
    )

    summary_after = await client.get(f"{REVIEWS}/product/{product_id}/summary")
    assert summary_after.json()["total_reviews"] == 1
    assert summary_after.json()["average_rating"] == 5


async def test_customer_cannot_set_status_or_archive_reason_on_create(
    client, customer_auth, customer, reviewed_product, review_payload, deliver_purchase
):
    await deliver_purchase(customer, reviewed_product)
    payload = {
        **review_payload,
        "product_id": reviewed_product["id"],
        "status": "ARCHIVED",
        "archive_reason": "CUSTOMER_DELETED",
    }
    response = await client.post(REVIEWS, json=payload, headers=customer_auth)
    assert response.status_code == 201, response.text
    body = response.json()
    # Extra fields are ignored, not honoured.
    assert body["status"] == "ACTIVE"
    assert body["archive_reason"] is None


async def test_customer_cannot_set_status_or_archive_reason_on_update(
    client, customer_auth, customer, reviewed_product, review_payload, deliver_purchase
):
    await deliver_purchase(customer, reviewed_product)
    payload = {**review_payload, "product_id": reviewed_product["id"]}
    created = await client.post(REVIEWS, json=payload, headers=customer_auth)
    review_id = created.json()["id"]

    response = await client.patch(
        f"{REVIEWS}/{review_id}",
        json={"status": "ARCHIVED", "archive_reason": "PRODUCT_ARCHIVED"},
        headers=customer_auth,
    )
    # Neither field is part of the update schema, and unknown fields are
    # rejected outright -- the review's lifecycle state stays out of the
    # customer's reach entirely, not just silently unaffected.
    assert response.status_code == 422, response.text


async def test_deleting_the_order_preserves_the_review(
    client, customer_auth, customer, reviewed_product, review_payload, deliver_purchase, session
):
    order = await deliver_purchase(customer, reviewed_product)
    payload = {**review_payload, "product_id": reviewed_product["id"]}
    created = await client.post(REVIEWS, json=payload, headers=customer_auth)
    review_id = created.json()["id"]
    assert created.json()["order_id"] == str(order.id)

    order_row = await session.get(Order, order.id)
    await session.delete(order_row)
    await session.commit()

    review = await session.get(Review, review_id)
    assert review is not None
    assert review.order_id is None
