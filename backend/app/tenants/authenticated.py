from fastapi import Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.tenants.context import TenantContext
from app.users.models import User


async def get_authenticated_tenant_context(
    current_user: User = Depends(get_current_user),
) -> TenantContext:
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with a tenant",
        )

    return TenantContext(
        tenant_id=current_user.tenant_id,
    )