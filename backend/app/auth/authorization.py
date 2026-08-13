"""Role-based route guards."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends

from app.auth.constants import UserRole
from app.auth.dependencies import get_current_user
from app.core.exceptions import PermissionDeniedError
from app.users.models import User


def require_roles(*allowed_roles: UserRole | str) -> Callable:
    """Build a dependency that admits only the listed roles."""
    allowed = {role.value if isinstance(role, UserRole) else role for role in allowed_roles}

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise PermissionDeniedError("Insufficient permissions")
        return current_user

    return dependency
