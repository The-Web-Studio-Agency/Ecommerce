from __future__ import annotations

from app.core.config import get_settings
from app.core.exceptions import ServiceUnavailableError
from app.core.logging import get_logger

logger = get_logger("auth.sms")


async def send_otp(phone: str, otp: str) -> None:
    if get_settings().is_production:
        logger.error("otp.delivery_not_configured")
        raise ServiceUnavailableError("Unable to send the verification code")

    logger.warning("otp.dev_delivery phone=%s otp=%s", phone, otp)
