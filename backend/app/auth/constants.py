from enum import Enum


class UserRole(str, Enum):
    PLATFORM_ADMIN = "PLATFORM_ADMIN"
    TENANT_ADMIN = "TENANT_ADMIN"
    STAFF = "STAFF"
    CUSTOMER = "CUSTOMER"


TENANT_ROLES = {
    UserRole.TENANT_ADMIN,
    UserRole.STAFF,
    UserRole.CUSTOMER,
}