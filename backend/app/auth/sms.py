from __future__ import annotations

import httpx

from app.auth.constants import OTP_EXPIRE_MINUTES
from app.core.config import Settings, get_settings
from app.core.exceptions import ServiceUnavailableError
from app.core.logging import get_logger

logger = get_logger("auth.sms")

MSG91_OTP_URL = "https://control.msg91.com/api/v5/otp"

DELIVERY_FAILED = "Unable to send the verification code"


async def send_otp(phone: str, otp: str) -> None:
    """
    Deliver a login code over SMS.

    MSG91 is the carrier, not the authority. The code is generated, hashed,
    expired and attempt-limited by AuthService against our own tables, so the
    `otp` here is one we already hold a hash of. We never call MSG91's verify
    endpoint -- doing so would put the same secret in two places that could
    disagree.

    Raising leaves the OTP row uncommitted, since the caller commits only
    after this returns. A code we could not deliver is therefore never a code
    someone could be asked for.
    """
    settings = get_settings()

    if not settings.msg91_auth_key or not settings.msg91_template_id:
        if settings.is_production:
            logger.error("otp.delivery_not_configured")
            raise ServiceUnavailableError(DELIVERY_FAILED)

        # Development without MSG91 credentials: the code goes to the log so
        # a local sign-in can be completed. Guarded by is_production above so
        # this can never be how a real code is handed out.
        logger.warning("otp.dev_delivery phone=%s otp=%s", phone, otp)
        return

    await _deliver(phone, otp, settings)


async def _deliver(phone: str, otp: str, settings: Settings) -> None:
    params = {
        "template_id": settings.msg91_template_id,
        "mobile": _to_msg91_mobile(phone),
        "otp": otp,
        "otp_expiry": str(OTP_EXPIRE_MINUTES),
    }

    if settings.msg91_sender_id:
        params["sender"] = settings.msg91_sender_id

    try:
        async with httpx.AsyncClient(timeout=settings.msg91_timeout_seconds) as client:
            response = await client.post(
                MSG91_OTP_URL,
                params=params,
                # The authkey is a header rather than a query parameter so it
                # stays out of proxy and access logs.
                headers={
                    "authkey": settings.msg91_auth_key or "",
                    "Content-Type": "application/json",
                },
                # Templates that use ##OTP## are filled from the otp param
                # above, so there are no variables left to send.
                json={},
            )
    except httpx.HTTPError as exc:
        logger.error("otp.delivery_failed reason=transport error=%s", type(exc).__name__)
        raise ServiceUnavailableError(DELIVERY_FAILED) from exc

    _check(response)


def _check(response: httpx.Response) -> None:
    """
    Decide whether MSG91 accepted the message.

    A 200 is not enough on its own: MSG91 reports refusals such as an
    unapproved template or an exhausted balance in the body while still
    answering 200, so the `type` field is what actually settles it.
    """
    try:
        payload = response.json()
    except ValueError:
        payload = {}

    outcome = str(payload.get("type", "")).lower() if isinstance(payload, dict) else ""

    if response.status_code == httpx.codes.OK and outcome == "success":
        # message is MSG91's request id, which is what their support and the
        # delivery-report webhook key off.
        logger.info("otp.delivered request_id=%s", payload.get("message"))
        return

    # payload["message"] is MSG91's own wording, never our code or authkey.
    logger.error(
        "otp.delivery_rejected status=%s type=%s detail=%s",
        response.status_code,
        outcome or "-",
        payload.get("message") if isinstance(payload, dict) else "-",
    )
    raise ServiceUnavailableError(DELIVERY_FAILED)


def _to_msg91_mobile(phone: str) -> str:
    """
    E.164 without the plus.

    normalize_phone has already produced +<country><number>; MSG91 wants the
    same digits with no leading +.
    """
    return phone.lstrip("+")
