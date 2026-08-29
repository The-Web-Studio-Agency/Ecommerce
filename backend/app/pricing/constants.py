from decimal import Decimal

# Percentages are stored as 18.00, not 0.18.
PERCENT = Decimal("100")

MAX_TAX_PERCENTAGE = Decimal("100")

# What `python -m app.commands.seed` gives the seeded tenant. Zeen charges a
# flat 100 for delivery, free over 2000, and 18% tax.
SEED_SHIPPING_AMOUNT = Decimal("100.00")
SEED_FREE_SHIPPING_MINIMUM = Decimal("2000.00")
SEED_TAX_PERCENTAGE = Decimal("18.00")
