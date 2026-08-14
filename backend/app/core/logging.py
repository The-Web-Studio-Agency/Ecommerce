"""Logging configuration and request correlation.

Every log line carries the request id, so an error response returned to a client
can be traced to the exact server-side event. Credentials, tokens and password
hashes are never logged - only identifiers.
"""

from __future__ import annotations

import logging
import logging.config
from contextvars import ContextVar

from app.core.config import get_settings

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

LOGGER_NAME = "tws"


def set_request_id(request_id: str) -> None:
    _request_id_ctx.set(request_id)


def get_request_id() -> str:
    return _request_id_ctx.get()


class RequestIdFilter(logging.Filter):
    """Inject the current request id into every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


def configure_logging() -> None:
    """Install the application-wide logging configuration."""
    settings = get_settings()
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {"request_id": {"()": RequestIdFilter}},
            "formatters": {
                "standard": {
                    "format": (
                        "%(asctime)s | %(levelname)-8s | %(name)s | "
                        "req=%(request_id)s | %(message)s"
                    ),
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "filters": ["request_id"],
                    "stream": "ext://sys.stdout",
                }
            },
            "loggers": {
                LOGGER_NAME: {
                    "handlers": ["console"],
                    "level": settings.log_level.upper(),
                    "propagate": False,
                },
                "uvicorn.error": {
                    "handlers": ["console"],
                    "level": settings.log_level.upper(),
                    "propagate": False,
                },
                # Silenced deliberately: the request-context middleware in
                # `app.main` logs one richer line per request (it adds the
                # request id and the duration). Leaving this at INFO would log
                # every request twice.
                "uvicorn.access": {
                    "handlers": ["console"],
                    "level": "WARNING",
                    "propagate": False,
                },
                "sqlalchemy.engine": {
                    "handlers": ["console"],
                    "level": "WARNING",
                    "propagate": False,
                },
            },
            "root": {"handlers": ["console"], "level": "WARNING"},
        }
    )


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a namespaced application logger (`tws.<name>`)."""
    return logging.getLogger(LOGGER_NAME if name is None else f"{LOGGER_NAME}.{name}")
