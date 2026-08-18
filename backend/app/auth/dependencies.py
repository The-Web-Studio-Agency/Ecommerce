from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.constants import UserRole
from app.auth.security import decode_token
from app.core.database import get_db
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.tenants.resolver import CurrentTenant
from app.users.models import User
from app.users.repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    tenant: CurrentTenant,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Not authenticated")

    payload = decode_token(credentials.credentials, expected_type="access")

    if payload.tenant_id != str(tenant.id):
        raise AuthenticationError("Invalid authentication credentials")

    try:
        user_id = UUID(payload.user_id)
    except ValueError as exc:
        raise AuthenticationError("Invalid authentication credentials") from exc

    user = await UserRepository(session).get_by_id(tenant_id=tenant.id, user_id=user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("Invalid authentication credentials")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def _require_roles(*roles: UserRole) -> Callable[..., Coroutine[Any, Any, User]]:
    allowed = frozenset(role.value for role in roles)

    async def dependency(current_user: CurrentUser) -> User:
        if current_user.role not in allowed:
            raise PermissionDeniedError("Insufficient permissions")
        return current_user

    return dependency


require_admin = _require_roles(UserRole.ADMIN)

require_staff = _require_roles(UserRole.ADMIN, UserRole.STAFF)
