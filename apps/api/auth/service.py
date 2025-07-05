from typing import Annotated
from sqlalchemy import select

from core.architecture.service import AbstractService
from core.authentication.firebase.client import create_firebase_client
from core.exceptions import InvalidRequestException
from apps.api.user.models import User

firebase_client = create_firebase_client()


class AuthService(AbstractService):
    def __init__(self, session):
        super().__init__(session)

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

        user = await self.session.scalar(select(User).where(User.uid == firebase_uid))
        if not user:
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
