# apps/api/apartment/dependency.py

from typing import Annotated
from fastapi import Depends

from apps.api.auth.dependency import UserDependency
from apps.api.user.models import User
from avcfastapi.core.exception.authentication import ForbiddenException


async def get_apartment_admin_user(user: UserDependency) -> User:
    """
    Dependency to verify that the current user is an apartment admin.
    Apartment admins have role 'apartment_admin'.
    """
    if not user or user.role not in ["apartment_admin", "admin"]:
        raise ForbiddenException(
            "Access denied. Apartment admin privileges required.",
            error_code="NOT_APARTMENT_ADMIN",
        )
    return user


ApartmentAdminDependency = Annotated[User, Depends(get_apartment_admin_user)]
