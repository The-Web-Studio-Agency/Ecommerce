"""Guards on the import graph and the Alembic setup."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import app.models.registry as registry
from app.models.base import Base

BACKEND_DIR = Path(__file__).resolve().parents[1]

EXPECTED_TABLES = {"tenants", "users"}


def _import_in_fresh_interpreter(module: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", f"import {module}"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
    )


def test_the_app_imports_the_way_uvicorn_imports_it():
    """Regression: a circular import that pytest's ordering hid.

    Under pytest, conftest imports several modules before `app.main`, which can
    mask an import cycle. Uvicorn imports `app.main` first in a clean
    interpreter, so the container failed to boot while the suite stayed green.
    """
    result = _import_in_fresh_interpreter("app.main")

    assert result.returncode == 0, result.stderr


def test_the_registry_imports_standalone():
    result = _import_in_fresh_interpreter("app.models.registry")

    assert result.returncode == 0, result.stderr


def test_every_model_is_registered_on_the_metadata():
    """A model missing from the registry is invisible to Alembic.

    `Base.metadata` is populated as a side effect of importing the model
    modules. If one is dropped from the registry - a linter removing an
    "unused" import is the usual way - autogenerate stops seeing its table and
    happily emits a migration that DROPS it.
    """
    registered = set(Base.metadata.tables)

    assert registered >= EXPECTED_TABLES, (
        f"missing from Base.metadata: {EXPECTED_TABLES - registered}. "
        "Add the model to app/models/registry.py."
    )


def test_registry_exports_every_model():
    for name in ("Base", "Tenant", "User"):
        assert name in registry.__all__
        assert hasattr(registry, name)


def test_constraints_follow_the_naming_convention():
    """Deterministic names keep migrations reviewable and errors mappable."""
    users = Base.metadata.tables["users"]

    assert users.primary_key.name == "pk_users"
    assert {fk.constraint.name for fk in users.foreign_keys} == {"fk_users_tenant_id_tenants"}
