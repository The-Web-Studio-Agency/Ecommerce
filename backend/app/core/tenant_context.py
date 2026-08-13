"""Tenant context - the single source of truth for "which tenant is this request".

Resolution happens once, in a dependency, and is then carried explicitly:

    request -> TenantContext -> Service -> TenantScopedRepository -> SQL

No service or repository ever reads a tenant id from a request body, a query
string, or a JWT claim directly, and no code branches on a tenant slug.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class TenantContext:
    """Immutable identity + display configuration of the current tenant.

    `currency` is tenant CONFIGURATION carried along for pricing and display, so
    services never have to re-query the tenant row (and never branch on slug).
    """

    tenant_id: UUID
    slug: str
    name: str
    currency: str = "INR"

    def __str__(self) -> str:  # pragma: no cover - logging helper
        return f"{self.slug}({self.tenant_id})"
