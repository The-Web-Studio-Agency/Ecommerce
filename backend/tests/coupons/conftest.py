"""Fixtures for the coupons tests.

Coupons has no module-specific fixtures of its own -- tests build coupons
directly via CouponRepository and drive requests through the shared `client`,
`session`, `tenant`, `admin_headers`, `staff_headers` and `customer_headers`
fixtures from the root conftest, same as every other module.
"""

from __future__ import annotations
