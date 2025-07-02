from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.authentication.firebase.client import create_firebase_client
from core.exceptions import InvalidRequestException
from apps.api.user.models import User

firebase_client = create_firebase_client()


async def firebase_authenticate(session: AsyncSession, uid: str) -> bool:
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
        raise InvalidRequestException("Firebase UID is required for authentication.")

    user = await session.scalar(select(User).where(User.uid == firebase_uid))
    if not user:
        user = User(
            uid=firebase_uid,
            fullname=firebase_user.display_name or "Unknown User",
            email=email,
            phone_number=phone_number,
            email_verified=firebase_user.email_verified,
        )

        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


async def firebase_user_data(session: AsyncSession, uid: str) -> User:
    user = firebase_client.get_user_by_uid(uid)
    return user
