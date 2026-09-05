from __future__ import annotations

from app.core.exceptions import AppError


class ValidationError(AppError):
    status_code = 400
    error_code = "VALIDATION_ERROR"
    default_message = "Request could not be validated"
