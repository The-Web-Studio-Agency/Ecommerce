from enum import Enum


class ReviewStatus(str, Enum):
    """Review lifecycle status."""

    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class ReviewArchiveReason(str, Enum):
    """Reason a review was archived."""

    PRODUCT_ARCHIVED = "PRODUCT_ARCHIVED"
    CUSTOMER_DELETED = "CUSTOMER_DELETED"