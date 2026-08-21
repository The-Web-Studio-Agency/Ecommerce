from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalogue.constants import CatalogueStatus
from app.catalogue.schemas import (
    CategoryStorefrontRead,
    ProductStorefrontRead,
    VariantStorefrontRead,
)
from app.catalogue.service import CategoryService, ProductService, VariantService
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.pagination import PageParams, page_params
from app.core.responses import ApiResponse, ok, paginated
from app.tenants.resolver import CurrentTenant

router = APIRouter(
    prefix="/storefront",
    tags=["Storefront-Catalogue"],
)

PRODUCT_NOT_FOUND = "Product not found"


@router.get(
    "/categories",
    response_model=ApiResponse[list[CategoryStorefrontRead]],
    summary="List public categories",
)
async def list_categories(
    tenant: CurrentTenant,
    params: PageParams = Depends(page_params),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[CategoryStorefrontRead]]:
    categories, total = await CategoryService(session, tenant.id).list(
        params,
        active_only=True,
    )

    return paginated(
        [CategoryStorefrontRead.model_validate(category) for category in categories],
        total_items=total,
        params=params,
        message="Categories retrieved",
    )


@router.get(
    "/categories/{category_id}",
    response_model=ApiResponse[CategoryStorefrontRead],
    summary="Get public category",
)
async def get_category(
    category_id: UUID,
    tenant: CurrentTenant,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[CategoryStorefrontRead]:
    category = await CategoryService(session, tenant.id).get(category_id)

    if not category.is_active:
        raise NotFoundError("Category not found")

    return ok(
        CategoryStorefrontRead.model_validate(category),
        message="Category retrieved",
    )


@router.get(
    "/products",
    response_model=ApiResponse[list[ProductStorefrontRead]],
    summary="List public products",
)
async def list_products(
    tenant: CurrentTenant,
    category_id: UUID | None = Query(
        default=None,
        description="Filter products by category",
    ),
    params: PageParams = Depends(page_params),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[ProductStorefrontRead]]:
    products, total = await ProductService(session, tenant.id).list(
        params,
        category_id=category_id,
        active_only=True,
    )

    return paginated(
        [ProductStorefrontRead.model_validate(product) for product in products],
        total_items=total,
        params=params,
        message="Products retrieved",
    )


@router.get(
    "/products/{product_id}",
    response_model=ApiResponse[ProductStorefrontRead],
    summary="Get public product",
)
async def get_product(
    product_id: UUID,
    tenant: CurrentTenant,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[ProductStorefrontRead]:
    product = await ProductService(session, tenant.id).get_public(product_id)

    return ok(
        ProductStorefrontRead.model_validate(product),
        message="Product retrieved",
    )


@router.get(
    "/products/{product_id}/variants",
    response_model=ApiResponse[list[VariantStorefrontRead]],
    summary="List public product variants",
)
async def list_variants(
    product_id: UUID,
    tenant: CurrentTenant,
    params: PageParams = Depends(page_params),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[VariantStorefrontRead]]:
    await ProductService(session, tenant.id).get_public(product_id)

    variants, total = await VariantService(session, tenant.id).list_for_product(
        product_id,
        params,
        active_only=True,
    )

    return paginated(
        [VariantStorefrontRead.model_validate(variant) for variant in variants],
        total_items=total,
        params=params,
        message="Variants retrieved",
    )


@router.get(
    "/variants/{variant_id}",
    response_model=ApiResponse[VariantStorefrontRead],
    summary="Get public variant",
)
async def get_variant(
    variant_id: UUID,
    tenant: CurrentTenant,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[VariantStorefrontRead]:
    variant = await VariantService(session, tenant.id).get(variant_id)

    if variant.status != CatalogueStatus.ACTIVE.value:
        raise NotFoundError("Variant not found")

    # A variant is only public while its parent product is, otherwise archiving
    # a product would leave its variants individually readable.
    await ProductService(session, tenant.id).get_public(variant.product_id)

    return ok(
        VariantStorefrontRead.model_validate(variant),
        message="Variant retrieved",
    )
