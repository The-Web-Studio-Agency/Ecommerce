from __future__ import annotations

from enum import Enum


class DiscountType(str, Enum):
    FIXED_AMOUNT = "FIXED_AMOUNT"
    PERCENTAGE = "PERCENTAGE"