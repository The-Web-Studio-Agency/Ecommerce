from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_customer
from app.cart.schemas import CartItemCreate, CartItemUpdate, CartRead
from app.cart.service import CartService
from app.core.database import get_db
from app.core.responses import ApiResponse, ok
from app.users.models import User

# Customer-facing and authenticated. The tenant comes from the hostname (via
# the token's tenant check) and the customer from the token -- neither is ever
# read from the request body.
router = APIRouter(prefix="/cart", tags=["Cart"])


def _service(session: AsyncSession, user: User) -> CartService:
    return CartService(session, user.tenant_id, user.id)


@router.get("", response_model=ApiResponse[CartRead], summary="Get the current cart")
async def get_cart(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_customer),
) -> ApiResponse[CartRead]:
    cart = await _service(session, user).view()
    return ok(cart, message="Cart retrieved")


@router.post(
    "/items",
    response_model=ApiResponse[CartRead],
    status_code=status.HTTP_201_CREATED,
    summary="Add a variant to the cart",
)
async def add_item(
    data: CartItemCreate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_customer),
) -> ApiResponse[CartRead]:
    cart = await _service(session, user).add_item(data)
    return ok(cart, message="Item added to cart")


@router.patch(
    "/items/{item_id}",
    response_model=ApiResponse[CartRead],
    summary="Update a cart item's quantity",
)
async def update_item(
    item_id: UUID,
    data: CartItemUpdate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_customer),
) -> ApiResponse[CartRead]:
    cart = await _service(session, user).update_item(item_id, data)
    return ok(cart, message="Cart item updated")


@router.delete(
    "/items/{item_id}",
    response_model=ApiResponse[CartRead],
    summary="Remove a cart item",
)
async def remove_item(
    item_id: UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_customer),
) -> ApiResponse[CartRead]:
    cart = await _service(session, user).remove_item(item_id)
    return ok(cart, message="Cart item removed")


@router.delete("", response_model=ApiResponse[CartRead], summary="Clear the cart")
async def clear_cart(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_customer),
) -> ApiResponse[CartRead]:
    cart = await _service(session, user).clear()
    return ok(cart, message="Cart cleared")
