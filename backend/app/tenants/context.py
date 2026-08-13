from uuid import UUID


class TenantContext:
    """
    Immutable tenant context for the current request.

    The tenant ID is resolved by the application boundary and should
    never be taken directly from arbitrary request data inside services.
    """

    def __init__(self, tenant_id: UUID):
        self.tenant_id = tenant_id