from enum import Enum


class UserRole(str, Enum):
    CUSTOMER = "CUSTOMER"
    STAFF = "STAFF"
    ADMIN = "ADMIN"


STAFF_ROLES = frozenset({UserRole.STAFF.value, UserRole.ADMIN.value})


class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class OtpPurpose(str, Enum):
    CUSTOMER_LOGIN = "CUSTOMER_LOGIN"
    ADMIN_LOGIN = "ADMIN_LOGIN"


OTP_LENGTH = 6
OTP_EXPIRE_MINUTES = 5
OTP_MAX_ATTEMPTS = 5
