"""Role -> permission mapping and the route guard that enforces it.

Routes depend on PERMISSIONS, not on role names. That indirection is worth its
one level because it means adding a role, or moving a capability between roles,
is an edit to the table below rather than a sweep through every router.

The map is static and lives in code. There is deliberately no database-backed
permission model, no permission CRUD, and no per-tenant customisation: nothing
in the product requires them yet.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends

from app.auth.constants import UserRole
from app.auth.dependencies import get_current_user
from app.core.exceptions import PermissionDeniedError
from app.users.models import User


class Permission:
    """Permission identifiers referenced by route dependencies."""

    # Platform scope - above the tenant boundary.
    PLATFORM_TENANTS_MANAGE = "platform:tenants:manage"

    # Tenant scope.
    CATALOGUE_READ = "catalogue:read"
    CATALOGUE_CREATE = "catalogue:create"
    CATALOGUE_UPDATE = "catalogue:update"
    CATALOGUE_DELETE = "catalogue:delete"

    INVENTORY_READ = "inventory:read"
    INVENTORY_UPDATE = "inventory:update"

    ORDERS_READ = "orders:read"
    ORDERS_UPDATE = "orders:update"

    CUSTOMERS_READ = "customers:read"
    CUSTOMERS_UPDATE = "customers:update"

    PAYMENTS_READ = "payments:read"
    PAYMENTS_MANAGE = "payments:manage"


_TENANT_ADMIN_PERMISSIONS = frozenset(
    {
        Permission.CATALOGUE_READ,
        Permission.CATALOGUE_CREATE,
        Permission.CATALOGUE_UPDATE,
        Permission.CATALOGUE_DELETE,
        Permission.INVENTORY_READ,
        Permission.INVENTORY_UPDATE,
        Permission.ORDERS_READ,
        Permission.ORDERS_UPDATE,
        Permission.CUSTOMERS_READ,
        Permission.CUSTOMERS_UPDATE,
        Permission.PAYMENTS_READ,
        Permission.PAYMENTS_MANAGE,
    }
)

#: Staff run the shop day to day: they read the catalogue and move stock and
#: orders, but do not restructure the catalogue, edit customers, or touch money.
_STAFF_PERMISSIONS = frozenset(
    {
        Permission.CATALOGUE_READ,
        Permission.INVENTORY_READ,
        Permission.INVENTORY_UPDATE,
        Permission.ORDERS_READ,
        Permission.ORDERS_UPDATE,
        Permission.CUSTOMERS_READ,
        Permission.PAYMENTS_READ,
    }
)

#: Platform administrators operate the platform, not a tenant's shop. They have
#: no tenant scope at all (enforced by ck_users_role_matches_tenant_scope), so
#: granting them tenant permissions here would be meaningless.
_PLATFORM_ADMIN_PERMISSIONS = frozenset({Permission.PLATFORM_TENANTS_MANAGE})

#: Customers hold no back-office permission. Storefront routes will authorise on
#: ownership of the resource, not on a permission grant.
_CUSTOMER_PERMISSIONS: frozenset[str] = frozenset()

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    UserRole.PLATFORM_ADMIN.value: _PLATFORM_ADMIN_PERMISSIONS,
    UserRole.TENANT_ADMIN.value: _TENANT_ADMIN_PERMISSIONS,
    UserRole.STAFF.value: _STAFF_PERMISSIONS,
    UserRole.CUSTOMER.value: _CUSTOMER_PERMISSIONS,
}


def permissions_for_role(role: str) -> frozenset[str]:
    """Permissions granted to a role. An unknown role grants nothing."""
    return ROLE_PERMISSIONS.get(role, frozenset())


def role_has_permission(role: str, permission: str) -> bool:
    return permission in permissions_for_role(role)


def require_permission(permission: str) -> Callable:
    """Build a route dependency admitting only callers holding `permission`.

    Usage:

        @router.post("/products", dependencies=[Depends(require_permission(
            Permission.CATALOGUE_CREATE))])

    The role is read from the database row loaded by `get_current_user`, never
    from the JWT's `role` claim, so a forged or stale token cannot grant it.
    """

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if not role_has_permission(current_user.role, permission):
            raise PermissionDeniedError("Insufficient permissions")
        return current_user

    return dependency
