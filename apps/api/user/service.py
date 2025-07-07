from typing import Annotated
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import select, update
from apps.api.user.models import PrivacyPreference, User
from core.architecture.service import AbstractService
from core.exceptions.request import InvalidRequestException
from core.storage.sqlalchemy.inputs.file import InputFile


class UserService(AbstractService):
    def __init__(self, session):
        super().__init__(session)

    async def get_user_by_uid(self, uid: str, raise_exception: bool = True):
        user = await self.session.scalar(select(User).where(User.uid == uid))
        if raise_exception and not user:
            raise InvalidRequestException("User not found", status_code=404)
        return user

    async def get_user_by_id(self, user_id: int):
        user = await self.session.scalar(select(User).where(User.id == user_id))
        if not user:
            raise InvalidRequestException("User not found", status_code=404)
        return user

    async def set_user_privacy_preferences(
        self, user_id: int, privacy_preference: PrivacyPreference
    ):
        user = await self.get_user_by_id(user_id)
        user.privacy_preference = privacy_preference.value
        await self.session.commit()
        return user

    async def update_user_details(
        self,
        user_id: UUID,
        fullname: str,
        email: str,
        phone_number: str | None = None,
        company_name: str | None = None,
    ):
        user = await self.get_user_by_id(user_id)
        user.fullname = fullname
        user.email = email
        user.phone_number = phone_number
        user.company_name = company_name
        await self.session.commit()
        return user

    async def update_user_profile_picture(
        self,
        user_id: UUID,
        profile_picture: UploadFile,
    ):
        user = await self.get_user_by_id(user_id)
        user.profile_picture = InputFile(
            content=await profile_picture.read(),
            filename=profile_picture.filename,
            prefix_date=True,
            unique_filename=True,
        )
        await self.session.commit()
        await self.session.refresh(user)
        return user


UserServiceDependency = Annotated[UserService, UserService.get_dependency()]
