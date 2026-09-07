"""Erase a customer's personal data on request, per DPDP and GDPR."""

from __future__ import annotations

import secrets
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.addresses.models import Address
from app.auth.constants import UserStatus
from app.auth.repository import RefreshTokenRepository
from app.cart.models import Cart, CartItem
from app.core.logging import get_logger
from app.ratings.models import Review
from app.search_filter.models import SearchHistory
from app.users.models import User
from app.wishlist.models import Wishlist, WishlistItem

logger = get_logger("users.erasure")

# +999 is reserved for trials, so a scrubbed number can never route anywhere,
# and it still satisfies the E.164 check constraint on the column.
ERASED_PHONE_PREFIX = "+999"


def _erased_phone() -> str:
    return f"{ERASED_PHONE_PREFIX}{secrets.randbelow(10**11):011d}"


class AccountErasureService:
    """Strip the person out of an account without destroying the trade record."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.tokens = RefreshTokenRepository(session)

    async def erase(self, user: User) -> None:
        await self._forget_shopping(user.id)
        await self._detach_reviews(user.id)
        await self._anonymise(user)

        await self.tokens.revoke_all_for_user(user.id)
        await self.session.commit()

        logger.info(
            "users.account_erased user_id=%s tenant_id=%s", user.id, self.tenant_id
        )

    async def _forget_shopping(self, user_id: UUID) -> None:
        """Carts, wishlists, addresses and search history are the person's alone."""
        cart_ids = (
            select(Cart.id)
            .where(Cart.tenant_id == self.tenant_id, Cart.customer_id == user_id)
            .scalar_subquery()
        )
        wishlist_ids = (
            select(Wishlist.id)
            .where(
                Wishlist.tenant_id == self.tenant_id, Wishlist.customer_id == user_id
            )
            .scalar_subquery()
        )

        # Children before parents -- the item tables point back at these rows.
        await self.session.execute(
            delete(CartItem).where(
                CartItem.tenant_id == self.tenant_id, CartItem.cart_id.in_(cart_ids)
            )
        )
        await self.session.execute(
            delete(Cart).where(
                Cart.tenant_id == self.tenant_id, Cart.customer_id == user_id
            )
        )

        await self.session.execute(
            delete(WishlistItem).where(
                WishlistItem.tenant_id == self.tenant_id,
                WishlistItem.wishlist_id.in_(wishlist_ids),
            )
        )
        await self.session.execute(
            delete(Wishlist).where(
                Wishlist.tenant_id == self.tenant_id, Wishlist.customer_id == user_id
            )
        )

        await self.session.execute(
            delete(Address).where(
                Address.tenant_id == self.tenant_id, Address.customer_id == user_id
            )
        )
        await self.session.execute(
            delete(SearchHistory).where(
                SearchHistory.tenant_id == self.tenant_id,
                SearchHistory.user_id == user_id,
            )
        )

    async def _detach_reviews(self, user_id: UUID) -> None:
        """Reviews stay up for other shoppers; they just stop naming an author."""
        await self.session.execute(
            update(Review)
            .where(Review.tenant_id == self.tenant_id, Review.user_id == user_id)
            .values(user_id=None)
        )

    async def _anonymise(self, user: User) -> None:
        """Orders keep their delivery details -- tax law requires the record."""
        user.phone = _erased_phone()
        user.email = None
        user.name = None
        user.status = UserStatus.DELETED.value
        user.is_verified = False
