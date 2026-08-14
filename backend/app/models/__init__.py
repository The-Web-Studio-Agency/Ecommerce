"""Declarative base.

Kept deliberately free of model imports: every model module does
`from app.models.base import ...`, which initialises this package first. Pulling
`Tenant` or `User` in here would make that import circular.

The Alembic model registry lives in `app.models.registry` instead.
"""

from app.models.base import Base, TimestampMixin

__all__ = [
    "Base",
    "TimestampMixin",
]
