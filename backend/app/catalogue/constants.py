from enum import Enum


class CatalogueStatus(str, Enum):
    """Publication state of a product or one of its variants.

    Shared by both because they answer the same question - may this be sold? -
    and a variant needs to be withheld or retired independently of its product
    (one size sells out permanently while the rest stay on sale).

    ARCHIVED rather than deletion is what retires something that must remain
    referenceable; DRAFT is the state a product is built up in before it is
    published.
    """

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


#: Longest a slug or SKU may be. Kept here so the model constraint, the request
#: schema and the migration cannot drift apart.
MAX_SLUG_LENGTH = 100
MAX_SKU_LENGTH = 64
MAX_NAME_LENGTH = 150
MAX_DESCRIPTION_LENGTH = 2000

#: Money is NUMERIC(12, 2): 10 digits before the decimal point is more headroom
#: than any single item price needs, and two after is the minor unit.
PRICE_PRECISION = 12
PRICE_SCALE = 2
