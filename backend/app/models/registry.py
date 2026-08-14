"""Model registry for Alembic.

Importing this module registers every ORM model on `Base.metadata`.

Alembic's autogenerate depends on it: a model that is never imported is invisible
to the metadata, and autogenerate would emit a migration that DROPS its table.
Every new model must be added here.

`__all__` is what keeps these imports from looking unused to a linter - do not
let them be "cleaned up".
"""

from app.auth.models import RefreshToken
from app.models.base import Base
from app.tenants.models import Tenant
from app.users.models import User

__all__ = [
    "Base",
    "RefreshToken",
    "Tenant",
    "User",
]
