"""
================================================================================
TEMPORARY DEV-ONLY ROUTER
================================================================================
Delete this file and its one registration block in `app/api/v1.py` once the
real Admin panel ships.

Calls the exact same `CategoryService` / `ProductService` / `VariantService` /
`ProductImageService` as the real `/catalogue/*` admin router (`router.py`,
untouched) -- no duplicate business logic, no new model/schema beyond the
`image_id` field on Variant (a real, permanent catalogue feature, not
temporary). The one thing that differs is the auth dependency: every handler
here takes `CurrentUser` (any signed-in user) instead of `require_admin`/
`require_staff`, so an ordinary shopper session can populate the catalogue
before the Admin panel exists to do it properly.

This does not touch, weaken, or share a code path with the real admin auth --
`/catalogue/*` still requires admin/staff exactly as before. It also cannot
run in production at all: `app/api/v1.py` only registers this router when
`not settings.is_production`, so in a production deployment these routes
don't exist regardless of who is signed in or what the frontend renders.
"""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.catalogue.schemas import (
    CategoryCreate,
    CategoryRead,
    ProductCreate,
    ProductImageCreate,
    ProductImageRead,
    ProductQuery,
    ProductRead,
    VariantCreate,
    VariantRead,
)
from app.catalogue.serializers import admin_variant
from app.catalogue.service import (
    CategoryService,
    ProductImageService,
    ProductService,
    VariantService,
)
from app.catalogue.uploads import store_image
from app.core.database import get_db
from app.core.pagination import PageParams
from app.core.responses import ApiResponse, ok, paginated

router = APIRouter(
    prefix="/dev/catalogue",
    tags=["TEMP-Dev-Catalogue (delete before launch, see dev_router.py)"],
)


@router.post(
    "/categories",
    response_model=ApiResponse[CategoryRead],
    status_code=status.HTTP_201_CREATED,
)
async def dev_create_category(
    data: CategoryCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[CategoryRead]:
    category = await CategoryService(session, user.tenant_id).create(data)
    return ok(CategoryRead.model_validate(category), message="Category created")


@router.get("/categories", response_model=ApiResponse[list[CategoryRead]])
async def dev_list_categories(
    params: Annotated[PageParams, Query()],
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[CategoryRead]]:
    categories, total = await CategoryService(session, user.tenant_id).list(params)
    return paginated(
        [CategoryRead.model_validate(c) for c in categories],
        total_items=total,
        params=params,
        message="Categories retrieved",
    )


@router.post(
    "/products",
    response_model=ApiResponse[ProductRead],
    status_code=status.HTTP_201_CREATED,
)
async def dev_create_product(
    data: ProductCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[ProductRead]:
    product = await ProductService(session, user.tenant_id).create(data)
    return ok(ProductRead.model_validate(product), message="Product created")


@router.get("/products", response_model=ApiResponse[list[ProductRead]])
async def dev_list_products(
    params: Annotated[ProductQuery, Query()],
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[ProductRead]]:
    products, total = await ProductService(session, user.tenant_id).list(
        params,
        category_id=params.category_id,
        search=params.search,
        brand=params.brand,
        featured=params.featured,
        sort=params.sort,
    )
    return paginated(
        [ProductRead.model_validate(p) for p in products],
        total_items=total,
        params=params,
        message="Products retrieved",
    )


@router.post(
    "/products/{product_id}/variants",
    response_model=ApiResponse[VariantRead],
    status_code=status.HTTP_201_CREATED,
)
async def dev_create_variant(
    product_id: UUID,
    data: VariantCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[VariantRead]:
    variant = await VariantService(session, user.tenant_id).create(product_id, data)
    return ok(admin_variant(variant), message="Variant created")


@router.get(
    "/products/{product_id}/images",
    response_model=ApiResponse[list[ProductImageRead]],
)
async def dev_list_product_images(
    product_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[list[ProductImageRead]]:
    images = await ProductImageService(session, user.tenant_id).list_for_product(
        product_id
    )
    return ok(
        [ProductImageRead.model_validate(image) for image in images],
        message="Product images retrieved",
    )


@router.post(
    "/products/{product_id}/images",
    response_model=ApiResponse[ProductImageRead],
    status_code=status.HTTP_201_CREATED,
)
async def dev_add_product_image(
    product_id: UUID,
    data: ProductImageCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> ApiResponse[ProductImageRead]:
    image = await ProductImageService(session, user.tenant_id).add(product_id, data)
    return ok(ProductImageRead.model_validate(image), message="Product image added")


@router.post(
    "/products/{product_id}/images/upload",
    response_model=ApiResponse[ProductImageRead],
    status_code=status.HTTP_201_CREATED,
)
async def dev_upload_product_image(
    product_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
    file: UploadFile = File(description="JPEG, PNG or WebP"),
    alt_text: str | None = Form(default=None),
    sort_order: int = Form(default=0, ge=0),
    is_primary: bool = Form(default=False),
) -> ApiResponse[ProductImageRead]:
    url = await store_image(
        user.tenant_id,
        file.filename or "",
        file.content_type or "",
        await file.read(),
    )

    image = await ProductImageService(session, user.tenant_id).add_uploaded(
        product_id,
        url=url,
        alt_text=alt_text,
        sort_order=sort_order,
        is_primary=is_primary,
    )
    return ok(ProductImageRead.model_validate(image), message="Product image uploaded")
