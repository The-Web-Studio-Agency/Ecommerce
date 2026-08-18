from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin, require_staff
from app.catalogue.schemas import (
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
    ProductCreate,
    ProductRead,
    ProductUpdate,
    VariantCreate,
    VariantRead,
    VariantUpdate,
)
from app.catalogue.service import CategoryService, ProductService, VariantService
from app.core.database import get_db
from app.core.pagination import PageParams, page_params
from app.core.responses import ApiResponse, ok, paginated
from app.users.models import User

router = APIRouter(prefix="/catalogue", tags=["Catalogue"])


@router.post(
    "/categories",
    response_model=ApiResponse[CategoryRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create a category",
)
async def create_category(
    data: CategoryCreate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> ApiResponse[CategoryRead]:
    category = await CategoryService(session, user.tenant_id).create(data)
    return ok(CategoryRead.model_validate(category), message="Category created")


@router.get(
    "/categories",
    response_model=ApiResponse[list[CategoryRead]],
    summary="List categories",
)
async def list_categories(
    params: PageParams = Depends(page_params),
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_staff),
) -> ApiResponse[list[CategoryRead]]:
    categories, total = await CategoryService(session, user.tenant_id).list(params)
    return paginated(
        [CategoryRead.model_validate(c) for c in categories],
        total_items=total,
        params=params,
        message="Categories retrieved",
    )


@router.get(
    "/categories/{category_id}",
    response_model=ApiResponse[CategoryRead],
    summary="Retrieve a category",
)
async def get_category(
    category_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_staff),
) -> ApiResponse[CategoryRead]:
    category = await CategoryService(session, user.tenant_id).get(category_id)
    return ok(CategoryRead.model_validate(category), message="Category retrieved")


@router.patch(
    "/categories/{category_id}",
    response_model=ApiResponse[CategoryRead],
    summary="Update a category",
)
async def update_category(
    category_id: UUID,
    data: CategoryUpdate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> ApiResponse[CategoryRead]:
    category = await CategoryService(session, user.tenant_id).update(category_id, data)
    return ok(CategoryRead.model_validate(category), message="Category updated")


@router.delete(
    "/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a category",
)
async def delete_category(
    category_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> Response:
    await CategoryService(session, user.tenant_id).delete(category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/products",
    response_model=ApiResponse[ProductRead],
    status_code=status.HTTP_201_CREATED,
    summary="Create a product",
)
async def create_product(
    data: ProductCreate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> ApiResponse[ProductRead]:
    product = await ProductService(session, user.tenant_id).create(data)
    return ok(ProductRead.model_validate(product), message="Product created")


@router.get(
    "/products",
    response_model=ApiResponse[list[ProductRead]],
    summary="List products",
)
async def list_products(
    category_id: UUID | None = Query(default=None, description="Filter by category"),
    params: PageParams = Depends(page_params),
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_staff),
) -> ApiResponse[list[ProductRead]]:
    products, total = await ProductService(session, user.tenant_id).list(
        params, category_id=category_id
    )
    return paginated(
        [ProductRead.model_validate(p) for p in products],
        total_items=total,
        params=params,
        message="Products retrieved",
    )


@router.get(
    "/products/{product_id}",
    response_model=ApiResponse[ProductRead],
    summary="Retrieve a product",
)
async def get_product(
    product_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_staff),
) -> ApiResponse[ProductRead]:
    product = await ProductService(session, user.tenant_id).get(product_id)
    return ok(ProductRead.model_validate(product), message="Product retrieved")


@router.patch(
    "/products/{product_id}",
    response_model=ApiResponse[ProductRead],
    summary="Update a product",
)
async def update_product(
    product_id: UUID,
    data: ProductUpdate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> ApiResponse[ProductRead]:
    product = await ProductService(session, user.tenant_id).update(product_id, data)
    return ok(ProductRead.model_validate(product), message="Product updated")


@router.delete(
    "/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product and its variants",
)
async def delete_product(
    product_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> Response:
    await ProductService(session, user.tenant_id).delete(product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/products/{product_id}/variants",
    response_model=ApiResponse[VariantRead],
    status_code=status.HTTP_201_CREATED,
    summary="Add a variant to a product",
)
async def create_variant(
    product_id: UUID,
    data: VariantCreate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> ApiResponse[VariantRead]:
    variant = await VariantService(session, user.tenant_id).create(product_id, data)
    return ok(VariantRead.model_validate(variant), message="Variant created")


@router.get(
    "/products/{product_id}/variants",
    response_model=ApiResponse[list[VariantRead]],
    summary="List a product's variants",
)
async def list_variants(
    product_id: UUID,
    params: PageParams = Depends(page_params),
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_staff),
) -> ApiResponse[list[VariantRead]]:
    variants, total = await VariantService(session, user.tenant_id).list_for_product(
        product_id, params
    )
    return paginated(
        [VariantRead.model_validate(v) for v in variants],
        total_items=total,
        params=params,
        message="Variants retrieved",
    )


@router.get(
    "/variants/{variant_id}",
    response_model=ApiResponse[VariantRead],
    summary="Retrieve a variant",
)
async def get_variant(
    variant_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_staff),
) -> ApiResponse[VariantRead]:
    variant = await VariantService(session, user.tenant_id).get(variant_id)
    return ok(VariantRead.model_validate(variant), message="Variant retrieved")


@router.patch(
    "/variants/{variant_id}",
    response_model=ApiResponse[VariantRead],
    summary="Update a variant",
)
async def update_variant(
    variant_id: UUID,
    data: VariantUpdate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> ApiResponse[VariantRead]:
    variant = await VariantService(session, user.tenant_id).update(variant_id, data)
    return ok(VariantRead.model_validate(variant), message="Variant updated")


@router.delete(
    "/variants/{variant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a variant",
)
async def delete_variant(
    variant_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> Response:
    await VariantService(session, user.tenant_id).delete(variant_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
