from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalogue.schemas import (
    CategoryRead,
    ProductImageStorefrontRead,
    ProductStorefrontRead,
    VariantRead,
)
from app.catalogue.service import (
    CategoryService,
    ProductImageService,
    ProductService,
    VariantService,
)
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.pagination import PageParams, page_params
from app.core.responses import ApiResponse, ok, paginated
from app.tenants.resolver import CurrentTenant


router = APIRouter(
    prefix="/storefront",
    tags=["Storefront-Catalogue"],
)


@router.get(
    "/categories",
    response_model=ApiResponse[list[CategoryRead]],
    summary="List public categories",
)
async def list_categories(
    params: PageParams = Depends(page_params),
    session: AsyncSession = Depends(get_db),
    tenant = CurrentTenant,
) -> ApiResponse[list[CategoryRead]]:
    categories, total = await CategoryService(
        session,
        tenant.id,
    ).list(
        params,
        active_only=True,
    )

    return paginated(
        [
            CategoryRead.model_validate(category)
            for category in categories
        ],
        total_items=total,
        params=params,
        message="Categories retrieved",
    )


@router.get(
    "/categories/{category_id}",
    response_model=ApiResponse[CategoryRead],
    summary="Get public category",
)
async def get_category(
    category_id: UUID,
    session: AsyncSession = Depends(get_db),
    tenant = CurrentTenant,
) -> ApiResponse[CategoryRead]:
    category = await CategoryService(
        session,
        tenant.id,
    ).get(category_id)

    if not category.is_active:
        raise NotFoundError("Category not found")

    return ok(
        CategoryRead.model_validate(category),
        message="Category retrieved",
    )


@router.get(
    "/products",
    response_model=ApiResponse[list[ProductStorefrontRead]],
    summary="List public products",
)
async def list_products(
    category_id: UUID | None = Query(
        default=None,
        description="Filter products by category",
    ),
    params: PageParams = Depends(page_params),
    session: AsyncSession = Depends(get_db),
    tenant = CurrentTenant,
) -> ApiResponse[list[ProductStorefrontRead]]:
    products, total = await ProductService(
        session,
        tenant.id,
    ).list(
        params,
        category_id=category_id,
        active_only=True,
    )

    return paginated(
        [
            ProductStorefrontRead.model_validate(product)
            for product in products
        ],
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
    session: AsyncSession = Depends(get_db),
    tenant = CurrentTenant,
) -> ApiResponse[ProductStorefrontRead]:
    product = await ProductService(
        session,
        tenant.id,
    ).get(product_id)

    if product.status != "ACTIVE":
        raise NotFoundError("Product not found")

    images = await ProductImageService(
        session,
        tenant.id,
    ).list_for_product(product_id)

    data = ProductStorefrontRead(
        id=product.id,
        category_id=product.category_id,
        name=product.name,
        slug=product.slug,
        short_description=product.short_description,
        description=product.description,
        brand=product.brand,
        is_featured=product.is_featured,
        seo_title=product.seo_title,
        seo_description=product.seo_description,
        images=[
            ProductImageStorefrontRead.model_validate(image)
            for image in images
        ],
    )

    return ok(
        data,
        message="Product retrieved",
    )


@router.get(
    "/products/{product_id}/variants",
    response_model=ApiResponse[list[VariantRead]],
    summary="List public product variants",
)
async def list_variants(
    product_id: UUID,
    params: PageParams = Depends(page_params),
    session: AsyncSession = Depends(get_db),
    tenant = CurrentTenant,
) -> ApiResponse[list[VariantRead]]:
    product = await ProductService(
        session,
        tenant.id,
    ).get(product_id)

    if product.status != "ACTIVE":
        raise NotFoundError("Product not found")

    variants, total = await VariantService(
        session,
        tenant.id,
    ).list_for_product(
        product_id,
        params,
        active_only=True,
    )

    return paginated(
        [
            VariantRead.model_validate(variant)
            for variant in variants
        ],
        total_items=total,
        params=params,
        message="Variants retrieved",
    )


@router.get(
    "/variants/{variant_id}",
    response_model=ApiResponse[VariantRead],
    summary="Get public variant",
)
async def get_variant(
    variant_id: UUID,
    session: AsyncSession = Depends(get_db),
    tenant = CurrentTenant,
) -> ApiResponse[VariantRead]:
    variant = await VariantService(
        session,
        tenant.id,
    ).get(variant_id)

    if variant.status != "ACTIVE":
        raise NotFoundError("Variant not found")

    return ok(
        VariantRead.model_validate(variant),
        message="Variant retrieved",
    )