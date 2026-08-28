"""
Rounding money.

Every amount in this project is a Decimal stored as Numeric(12, 2). Anything
that divides -- a tax percentage, for one -- can produce more decimal places
than that, so the result is rounded here rather than left for the database to
truncate however it likes.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

# Two decimal places, matching PRICE_SCALE on every money column.
MONEY = Decimal("0.01")

ZERO = Decimal("0.00")


def money(amount: Decimal) -> Decimal:
    """Round to paise, half up -- the way an amount is rounded on a receipt."""
    return amount.quantize(MONEY, rounding=ROUND_HALF_UP)
