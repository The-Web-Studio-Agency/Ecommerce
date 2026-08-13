"""Model registry.

Importing this package registers every ORM model on `Base.metadata`.

Alembic's autogenerate depends on it: a model that is never imported is invisible
to the metadata, and autogenerate would emit a migration that DROPS its table.
Every new model must be added here.

`__all__` is what keeps these imports from looking unused to a linter - do not
let them be "cleaned up".
"""

from app.models.base import Base, TimestampMixin
from app.tenants.models import Tenant
from app.users.models import User

__all__ = [
    "Base",
    "TimestampMixin",
    "Tenant",
    "User",
]
