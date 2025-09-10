from typing import Annotated
from uuid import UUID
from fastapi import UploadFile
from sqlalchemy import select

from apps.api.device.schema import DeviceStatus
from apps.api.device.service import DeviceServiceDependency
from apps.api.user.models import PrivacyPreference, User, UserStatus
from avcfastapi.core.database.sqlalchamey.core import SessionDep
from avcfastapi.core.exception.request import InvalidRequestException
from avcfastapi.core.fastapi.dependency.service_dependency import AbstractService
from avcfastapi.core.storage.sqlalchemy.inputs.file import InputFile


class UserService(AbstractService):
    DEPENDENCIES = {"session": SessionDep, "device_service": DeviceServiceDependency}

    def __init__(
        self, session: SessionDep, device_service: DeviceServiceDependency, **kwargs
    ):
        super().__init__(session=session, **kwargs)
        self.session = session
        self.device_service = device_service

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

    async def delete_user(self, user_id: UUID):
        user = await self.get_user_by_id(user_id)
        user.soft_delete()
        await self.session.commit()
        return user

    async def logout_user(self, user_id: UUID, device_id: str | None = None):
        if device_id:
            user = await self.get_user_by_id(user_id)
            await self.device_service.update_device_status(
                device_id=device_id, user_id=user.id, new_status=DeviceStatus.LOGGED_OUT
            )
        # do nothing

    async def change_user_status(self, user_id: UUID, new_status: UserStatus):
        user = await self.get_user_by_id(user_id)
        user.status = new_status.value
        await self.session.commit()
        return user


UserServiceDependency = Annotated[UserService, UserService.get_dependency()]
