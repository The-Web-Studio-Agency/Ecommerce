"""Authentication dependencies.

`get_current_user` is the single place where a bearer token becomes a trusted
identity. It re-checks state the token cannot express: a token stays
cryptographically valid until it expires, so deactivating a user - or their
whole tenant - only takes effect if it is verified per request.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import decode_token
from app.core.database import get_db
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.users.models import User
from app.users.repository import UserRepository

# HTTPBearer rather than OAuth2PasswordBearer: the login endpoint takes JSON,
# not form encoding, so the OAuth2 password flow would document a request shape
# this API does not actually accept.
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
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

    return user


def tenant_id_of(user: User) -> UUID:
    """The tenant a request operates in, for tenant-scoped modules.

    A platform user has no tenant. Today none of them holds a tenant-scoped
    permission, so this cannot trigger through a guarded route - but a
    `TenantScopedRepository` built with None would silently match no rows
    instead of failing, so the impossible case is made loud rather than quiet.
    """
    if user.tenant_id is None:
        raise PermissionDeniedError("This operation requires a tenant-scoped account")
    return user.tenant_id
