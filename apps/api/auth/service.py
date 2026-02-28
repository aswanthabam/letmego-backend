from typing import Annotated
from sqlalchemy import select

from apps.api.user.models import User
from avcfastapi.core.authentication.firebase import firebase_client
from avcfastapi.core.database.sqlalchamey.core import SessionDep
from avcfastapi.core.exception.request import InvalidRequestException
from avcfastapi.core.fastapi.dependency.service_dependency import AbstractService


class AuthService(AbstractService):
    DEPENDENCIES = {"session": SessionDep}

    def __init__(self, session: SessionDep, **kwargs):
        super().__init__(session=session, **kwargs)
        self.session = session

    async def firebase_authenticate(self, uid: str) -> bool:
        firebase_user = firebase_client.get_user_by_uid(uid)
        if not firebase_user:
            raise InvalidRequestException("Invalid ID token or user not found.")
        email = firebase_user.email
        phone_number = firebase_user.phone_number

        if not email and not phone_number:
            raise InvalidRequestException(
                "Email and phone number are required for authentication."
            )

        firebase_uid = firebase_user.uid

        if not firebase_uid:
            raise InvalidRequestException(
                "Firebase UID is required for authentication."
            )

        # Check for existing user INCLUDING soft-deleted accounts
        user = await self.session.scalar(
            select(User).where(User.uid == firebase_uid)
        )
        
        if user and user.deleted_at is not None:
            # Restore soft-deleted account to preserve historical data
            user.deleted_at = None
            user.fullname = firebase_user.display_name or user.fullname
            user.email = email or user.email
            user.phone_number = phone_number or user.phone_number
            user.email_verified = firebase_user.email_verified
            await self.session.commit()
            await self.session.refresh(user)
        elif not user:
            user = User(
                uid=firebase_uid,
                fullname=firebase_user.display_name or "Unknown User",
                email=email,
                phone_number=phone_number,
                email_verified=firebase_user.email_verified,
            )

            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
        return user

    async def firebase_user_data(self, uid: str) -> User:
        user = firebase_client.get_user_by_uid(uid)
        return user


AuthServiceDependency = Annotated[AuthService, AuthService.get_dependency()]
