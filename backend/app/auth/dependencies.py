"""Authentication dependencies.

`get_current_identity` is the single place where a bearer token becomes a
trusted identity. It re-checks state that the token cannot express: a token
stays cryptographically valid until it expires, so deactivating a user - or
their whole tenant - only takes effect if it is verified per request.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import decode_token
from app.core.database import get_db
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.tenant_context import TenantContext
from app.users.models import User
from app.users.repository import UserRepository

# HTTPBearer rather than OAuth2PasswordBearer: the login endpoint takes JSON,
# not form encoding, so the OAuth2 password flow would document a request shape
# this API does not actually accept.
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentIdentity:
    """The authenticated user plus the tenant they are acting within."""

    user: User
    tenant: TenantContext | None


async def get_current_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> CurrentIdentity:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Not authenticated")

    payload = decode_token(credentials.credentials, expected_type="access")

    try:
        user_id = UUID(payload.subject)
    except (ValueError, AttributeError) as exc:
        raise AuthenticationError("Invalid authentication credentials") from exc

    loaded = await UserRepository(session).get_with_tenant(user_id)
    if loaded is None:
        raise AuthenticationError("Invalid authentication credentials")

    user, tenant = loaded
    if not user.is_active:
        raise AuthenticationError("Invalid authentication credentials")

    # A user bound to a tenant is only authenticated while that tenant is active.
    if user.tenant_id is not None and (tenant is None or not tenant.is_active):
        raise AuthenticationError("Invalid authentication credentials")

    context = (
        TenantContext(tenant_id=tenant.id, slug=tenant.slug, name=tenant.name)
        if tenant is not None
        else None
    )
    return CurrentIdentity(user=user, tenant=context)


async def get_current_user(
    identity: CurrentIdentity = Depends(get_current_identity),
) -> User:
    """The authenticated user, without requiring a tenant scope."""
    return identity.user


async def get_authenticated_tenant(
    identity: CurrentIdentity = Depends(get_current_identity),
) -> TenantContext:
    """The caller's own tenant scope.

    Reuses the tenant already loaded during authentication, so requiring a
    tenant scope costs no additional query.
    """
    if identity.tenant is None:
        raise PermissionDeniedError("User is not associated with a tenant")
    return identity.tenant
