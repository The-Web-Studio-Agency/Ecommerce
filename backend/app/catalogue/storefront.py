from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalogue.constants import CatalogueStatus, ProductSort
from app.catalogue.schemas import (
    CategoryStorefrontRead,
    ProductStorefrontRead,
    ProductSummaryStorefrontRead,
    VariantStorefrontRead,
)
from app.catalogue.serializers import (
    storefront_product,
    storefront_summary,
    storefront_variant,
)
from app.catalogue.service import CategoryService, ProductService, VariantService
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.pagination import PageParams, page_params
from app.core.responses import ApiResponse, ok, paginated
from app.tenants.resolver import CurrentTenant

# Public, unauthenticated. The tenant comes from the request hostname via
# CurrentTenant -- a tenant id is never accepted from the client.
router = APIRouter(prefix="/storefront", tags=["Storefront-Catalogue"])


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
        params, active_only=True
    )
    return paginated(
        [CategoryStorefrontRead.model_validate(c) for c in categories],
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
    category = await CategoryService(session, tenant.id).get_public(category_id)
    return ok(
        CategoryStorefrontRead.model_validate(category), message="Category retrieved"
    )


@router.get(
    "/products",
    response_model=ApiResponse[list[ProductSummaryStorefrontRead]],
    summary="List, search, filter and sort public products",
)
async def list_products(
    tenant: CurrentTenant,
    category_id: UUID | None = Query(default=None, description="Filter by category"),
    search: str | None = Query(
        default=None, max_length=120, description="Match product name or brand"
    ),
    brand: str | None = Query(default=None, max_length=150),
    featured: bool | None = Query(default=None, description="Only featured products"),
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    sort: ProductSort = Query(default=ProductSort.NAME_ASC),
    params: PageParams = Depends(page_params),
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[ProductSummaryStorefrontRead]]:
    products, total = await ProductService(session, tenant.id).list(
        params,
        category_id=category_id,
        search=search,
        brand=brand,
        featured=featured,
        min_price=min_price,
        max_price=max_price,
        sort=sort,
        active_only=True,
    )
    return paginated(
        [storefront_summary(product) for product in products],
        total_items=total,
        params=params,
        message="Products retrieved",
    )


@router.get(
    "/products/{product_id}",
    response_model=ApiResponse[ProductStorefrontRead],
    summary="Get public product with images, options and variants",
)
async def get_product(
    product_id: UUID,
    tenant: CurrentTenant,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[ProductStorefrontRead]:
    products = ProductService(session, tenant.id)
    product = await products.get_public(product_id)
    category = await products.categories.get(product.category_id)

    return ok(storefront_product(product, category), message="Product retrieved")


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
        product_id, params, active_only=True
    )
    return paginated(
        [storefront_variant(variant) for variant in variants],
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

    return ok(storefront_variant(variant), message="Variant retrieved")
