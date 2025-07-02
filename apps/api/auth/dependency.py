from typing import Annotated
from fastapi import Depends
from sqlalchemy import select

from apps.api.user.models import User
from core.db.core import SessionDep
from core.exceptions.authentication import ForbiddenException
from core.authentication.firebase.dependency import (
    FirebaseAuthDependency,
)


async def get_current_user(
    session: SessionDep, decoded_token: FirebaseAuthDependency
) -> User:
    user = await session.scalar(select(User).where(User.uid == decoded_token.uid))
    if not user:
        raise ForbiddenException(
            "User not found or not authenticated.",
            error_code="USER_NOT_FOUND",
        )
    return user


UserDependency = Annotated[User, Depends(get_current_user)]
