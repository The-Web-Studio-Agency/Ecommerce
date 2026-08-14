"""Request-derived values that must be treated as untrusted input.

Both values here come from the client and both are used in security decisions
(rate-limit keys, log correlation), so neither is taken at face value.
"""

from __future__ import annotations

import re
import uuid

from fastapi import Request

#: Conservative: what a correlation id may contain. Anything else - notably
#: newlines - could forge log lines once the value is written to a log.
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def sanitize_request_id(value: str | None) -> str:
    """Return the caller's correlation id if it is safe, else a fresh one."""
    if value and _REQUEST_ID_PATTERN.match(value):
        return value
    return uuid.uuid4().hex


def client_ip(request: Request) -> str:
    """The caller's IP address.

    Deliberately reads `request.client` rather than parsing `X-Forwarded-For`.
    Behind a proxy, run Uvicorn with `--proxy-headers --forwarded-allow-ips=<lb>`
    so the server rewrites `request.client` only for peers you trust. Parsing
    the header here would mean trusting a value any client can set, which would
    let an attacker rotate their apparent IP past the rate limiter.
    """
    return request.client.host if request.client else "unknown"
