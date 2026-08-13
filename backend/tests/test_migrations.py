"""Guards on the Alembic setup itself."""

from __future__ import annotations

import app.models as model_registry
from app.models.base import Base

EXPECTED_TABLES = {"tenants", "users"}


def test_every_model_is_registered_on_the_metadata():
    """Regression: a model missing from `app.models` is invisible to Alembic.

    `Base.metadata` is populated as a side effect of importing the model
    modules. If one is dropped from the registry - a linter removing an
    "unused" import is the usual way - autogenerate stops seeing its table and
    happily emits a migration that DROPS it.
    """
    registered = set(Base.metadata.tables)

    assert registered >= EXPECTED_TABLES, (
        f"missing from Base.metadata: {EXPECTED_TABLES - registered}. "
        "Add the model to app/models/__init__.py."
    )


def test_registry_exports_every_model():
    for name in ("Base", "Tenant", "User"):
        assert name in model_registry.__all__
        assert hasattr(model_registry, name)


def test_constraints_follow_the_naming_convention():
    """Deterministic names keep migrations reviewable and errors mappable."""
    users = Base.metadata.tables["users"]

    assert users.primary_key.name == "pk_users"
    assert {fk.constraint.name for fk in users.foreign_keys} == {
        "fk_users_tenant_id_tenants"
    }
