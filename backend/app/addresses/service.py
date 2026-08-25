from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.addresses.models import Address
from app.addresses.repository import AddressRepository
from app.addresses.schemas import AddressCreate, AddressUpdate
from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger

logger = get_logger("addresses")

ADDRESS_NOT_FOUND = "Address not found"


class AddressService:
    """
    A customer's delivery addresses.

    Everything here is scoped to one customer inside one tenant: the service is
    constructed with both ids, and no method takes them from the caller.
    """

    def __init__(self, session: AsyncSession, tenant_id: UUID, customer_id: UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.customer_id = customer_id
        self.addresses = AddressRepository(session, tenant_id)

    async def get(self, address_id: UUID) -> Address:
        address = await self.addresses.get_for_customer(self.customer_id, address_id)
        if address is None:
            raise NotFoundError(ADDRESS_NOT_FOUND)
        return address

    async def list(self) -> list[Address]:
        rows = await self.session.scalars(self.addresses.list_select(self.customer_id))
        return list(rows.all())

    async def create(self, data: AddressCreate) -> Address:
        # The first address a customer saves becomes their default, so checkout
        # always has something sensible to pre-select.
        is_default = data.is_default or not await self.addresses.has_any(self.customer_id)

        try:
            # Demote the old default before inserting the new one. A unique
            # index allows only one default per customer, so the order matters:
            # two rows must never both be default, even for one flush.
            if is_default:
                await self.addresses.clear_default(self.customer_id)

            address = Address(
                customer_id=self.customer_id,
                full_name=data.full_name,
                phone=data.phone,
                address_line_1=data.address_line_1,
                address_line_2=data.address_line_2,
                city=data.city,
                state=data.state,
                postal_code=data.postal_code,
                country=data.country,
                is_default=is_default,
            )
            await self.addresses.add(address)
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("Unable to save the address") from exc

        logger.info(
            "addresses.created id=%s tenant_id=%s", address.id, self.tenant_id
        )
        return address

    async def update(self, address_id: UUID, data: AddressUpdate) -> Address:
        address = await self.get(address_id)
        changes = data.model_dump(exclude_unset=True)

        # Held back and applied last, for the same reason as in `create`.
        make_default = changes.pop("is_default", None)

        for field, value in changes.items():
            setattr(address, field, value)

        try:
            if make_default is True:
                await self.addresses.clear_default(
                    self.customer_id, exclude_id=address.id
                )
                address.is_default = True
            elif make_default is False:
                address.is_default = False

            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("Unable to save the address") from exc

        logger.info(
            "addresses.updated id=%s tenant_id=%s", address.id, self.tenant_id
        )
        return address

    async def delete(self, address_id: UUID) -> None:
        """
        Remove the address for good.

        Orders keep their own copy of the address they were placed with, so
        deleting one here never changes order history.
        """
        address = await self.get(address_id)

        await self.addresses.delete(address)
        await self.session.commit()

        logger.info(
            "addresses.deleted id=%s tenant_id=%s", address_id, self.tenant_id
        )
