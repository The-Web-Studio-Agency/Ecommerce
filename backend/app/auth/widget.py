from __future__ import annotations

from typing import Any

import httpx

from app.auth.phone import normalize_phone
from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, ServiceUnavailableError
from app.core.logging import get_logger

logger = get_logger("auth.widget")

UNVERIFIED = "Could not verify that number"
UNAVAILABLE = "Unable to verify your number right now"

# Where the verified identifier turns up. MSG91 returns it as `message` on the
# widget verification, but the payload is read defensively: a shape we do not
# recognise must fail closed rather than authenticate the wrong person.
_IDENTIFIER_KEYS = ("message", "mobile", "identifier", "phone", "number")

_MAX_SEARCH_DEPTH = 3


async def verify_access_token(access_token: str) -> str:
    """
    Exchange a widget access token for the phone number MSG91 verified.

    This is the only place a phone number becomes trusted. The widget runs in
    the browser, so everything it reports -- including the number it claims to
    have verified -- is attacker-controlled until MSG91 confirms it against the
    account auth key, which never leaves the server.

    Returns the number in E.164. Raises AuthenticationError when MSG91 rejects
    the token, and ServiceUnavailableError when MSG91 could not be reached, so
    a provider outage is never reported to the caller as a bad code.
    """
    settings = get_settings()

    if not settings.msg91_auth_key:
        logger.error("widget.verification_not_configured")
        raise ServiceUnavailableError(UNAVAILABLE)

    try:
        async with httpx.AsyncClient(timeout=settings.msg91_timeout_seconds) as client:
            response = await client.post(
                settings.msg91_widget_verify_url,
                json={
                    "authkey": settings.msg91_auth_key,
                    "access-token": access_token,
                },
                headers={"Content-Type": "application/json"},
            )
    except httpx.HTTPError as exc:
        logger.error("widget.verify_transport_error error=%s", type(exc).__name__)
        raise ServiceUnavailableError(UNAVAILABLE) from exc

    return _identity_from(response)


def _identity_from(response: httpx.Response) -> str:
    try:
        payload: Any = response.json()
    except ValueError:
        payload = None

    outcome = ""
    if isinstance(payload, dict):
        outcome = str(payload.get("type", "")).lower()

    # MSG91 failing on its own account is not the caller getting the code
    # wrong. Answering 401 to a server error or a throttle would tell someone
    # their correct code was rejected, and send them round the loop again.
    if response.status_code >= httpx.codes.INTERNAL_SERVER_ERROR or (
        response.status_code == httpx.codes.TOO_MANY_REQUESTS
    ):
        logger.error("widget.provider_error status=%s", response.status_code)
        raise ServiceUnavailableError(UNAVAILABLE)

    # As with the rest of MSG91's API, a 200 is not on its own an acceptance --
    # a rejected or expired token is reported in the body.
    if response.status_code != httpx.codes.OK or outcome != "success":
        logger.info(
            "widget.token_rejected status=%s type=%s",
            response.status_code,
            outcome or "-",
        )
        raise AuthenticationError(UNVERIFIED)

    phone = _phone_from(payload)

    if phone is None:
        # Verified, but we cannot tell who for. Authenticating anyone here
        # would mean picking an identity MSG91 did not actually give us.
        logger.error("widget.identifier_missing keys=%s", sorted(payload))
        raise AuthenticationError(UNVERIFIED)

    return phone


def _phone_from(payload: dict[str, Any], depth: int = 0) -> str | None:
    """
    The first field that reads as a phone number, in E.164.

    Only the known identifier keys are considered. Searching every value
    instead would be worse than useless: a ten-digit unix timestamp normalises
    to a valid-looking E.164 number, so a loose search could authenticate
    someone as a customer conjured out of a date.

    Candidates are run through normalize_phone rather than trusted on sight,
    which also rules out `message` when it holds a status string -- MSG91 puts
    "AuthenticationFailure" in that same field on rejection.
    """
    if depth > _MAX_SEARCH_DEPTH:
        return None

    for key in _IDENTIFIER_KEYS:
        # Numbers are accepted as well as strings: JSON has one number type,
        # and a bare mobile number is as likely to arrive as an int as it is
        # quoted.
        value = payload.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int | float):
            value = format(int(value), "d")
        if not isinstance(value, str) or not value.strip():
            continue
        try:
            return normalize_phone(value)
        except ValueError:
            continue

    # MSG91 wraps some responses; look through nested objects rather than
    # assume a flat body.
    for nested in payload.values():
        if isinstance(nested, dict):
            found = _phone_from(nested, depth + 1)
            if found is not None:
                return found

    return None
