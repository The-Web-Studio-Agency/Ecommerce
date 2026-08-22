"""
Loaders for the JSON test data that sits beside each test package.

Every package keeps its own `data.json` next to its tests -- catalogue data in
tests/catalogue/, auth data in tests/auth/ -- so the fixtures live with the
tests that use them and there are no sample payloads hard-coded in Python.

    DATA = load_data(__file__)          # reads data.json beside this module
    payload = sample(DATA, "category", name="Skirts")

`sample` always returns a deep copy, so a test that applies overrides can never
mutate the shared defaults for the next test.
"""

from __future__ import annotations

import copy
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_FILE = "data.json"


@lru_cache
def _read(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text())


def load_data(module_file: str) -> dict[str, Any]:
    """The data.json living in the same directory as the calling test module."""
    return _read(str(Path(module_file).resolve().parent / DATA_FILE))


def shared_data() -> dict[str, Any]:
    """Data used across packages, from tests/data.json."""
    return _read(str(Path(__file__).resolve().parent / DATA_FILE))


def sample(source: dict[str, Any], key: str, /, **overrides: Any) -> dict[str, Any]:
    """
    A fresh copy of one payload, with overrides applied.

    `source` and `key` are positional-only so that "name", "key" and friends
    stay usable as payload override keys.
    """
    payload = copy.deepcopy(source[key])
    payload.update(overrides)
    return payload


async def run_concurrently(engine, times: int, work) -> list[Any]:
    """
    Run `work(session, index)` `times` over at once, each on its own session.

    Keeps the async_sessionmaker/gather plumbing out of the tests. Returns what
    each call returned, or the exception it raised, so a test can simply count
    how many succeeded.
    """
    import asyncio

    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def one(index: int) -> Any:
        async with factory() as session:
            return await work(session, index)

    return await asyncio.gather(
        *(one(index) for index in range(times)), return_exceptions=True
    )


def succeeded(results: list[Any]) -> list[Any]:
    """The results that did not raise."""
    return [r for r in results if not isinstance(r, BaseException)]
