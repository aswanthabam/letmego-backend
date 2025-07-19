from datetime import datetime, timezone
from sqlalchemy import select
from typing import List, Optional
from typing_extensions import Annotated
from uuid import UUID as PyUUID

from apps.api.device.models import Device
from apps.api.device.schema import DeviceStatus
from core.architecture.service import AbstractService
from core.db.core import SessionDep
from core.exceptions.request import InvalidRequestException
from core.utils.validations import is_valid_uuid


class DeviceService(AbstractService):
    """
    Service class for managing device CRUD operations.
    """

    DEPENDENCIES = {
        "session": SessionDep,
    }

    def __init__(self, session: SessionDep):
        super().__init__(session=session)
        self.session = session

    async def create_device(
        self,
        device_token: str,
        platform: str,
        user_id: Optional[PyUUID] = None,
        device_model: Optional[str] = None,
        os_version: Optional[str] = None,
        app_version: Optional[str] = None,
        language_code: Optional[str] = "en",
        push_enabled: Optional[str] = "UNKNOWN",
    ) -> Device:
        """
        Creates a new device. Raises an error if the device_token is already registered.
        """
        # Check for existing device with the same token
        query = select(Device).where(Device.device_token == device_token)
        existing_device = await self.session.scalar(query)

        if existing_device:
            return await self.update_device(
                device_id=existing_device.id,
                user_id=user_id,
                device_model=device_model,
                platform=platform,
                os_version=os_version,
                app_version=app_version,
                language_code=language_code,
                push_enabled=push_enabled,
            )

        new_device = Device(
            user_id=user_id,
            device_token=device_token,
            device_model=device_model,
            platform=platform,
            os_version=os_version,
            app_version=app_version,
            language_code=language_code,
            push_enabled=push_enabled,
        )
        self.session.add(new_device)
        await self.session.commit()
        await self.session.refresh(new_device)
        return new_device

    async def get_device(
        self, device_id: str, user_id: PyUUID, update_status=False
    ) -> Optional[Device]:
        """
        Retrieves a single device by its primary ID.
        """
        if is_valid_uuid(device_id):
            query = select(Device).where(
                Device.id == device_id, Device.user_id == user_id
            )
        else:
            query = select(Device).where(
                Device.device_token == device_id, Device.user_id == user_id
            )
        device = await self.session.scalar(query)
        if device and update_status:
            await self.update_device_status(
                device_id=device.id, user_id=user_id, new_status=DeviceStatus.ACTIVE
            )
        return device

    async def get_devices(
        self,
        user_id: Optional[PyUUID] = None,
        status: Optional[DeviceStatus] = None,
        platform: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> List[Device]:
        """
        Retrieves a list of devices with optional filtering and pagination.
        """
        query = select(Device)
        if user_id:
            query = query.where(Device.user_id == user_id)
        if status:
            query = query.where(Device.status == status.value)
        if platform:
            query = query.where(Device.platform == platform)

        query = query.offset(offset).limit(limit)
        result = await self.session.scalars(query)
        return list(result.all())

    async def update_device(
        self,
        device_id: PyUUID,
        user_id: Optional[PyUUID] = None,
        device_token: Optional[str] = None,
        device_model: Optional[str] = None,
        platform: Optional[str] = None,
        os_version: Optional[str] = None,
        app_version: Optional[str] = None,
        language_code: Optional[str] = None,
        push_enabled: Optional[str] = None,
    ) -> Device:
        """
        Updates an existing device's fields. Only non-None values are updated.
        """
        device = await self.get_device(device_id, user_id=user_id)
        if not device:
            raise InvalidRequestException(f"Device with ID {device_id} not found.")

        # Prepare a dictionary of updates, excluding None values
        update_data = {
            "user_id": user_id,
            "device_token": device_token,
            "device_model": device_model,
            "platform": platform,
            "os_version": os_version,
            "app_version": app_version,
            "language_code": language_code,
            "push_enabled": push_enabled,
        }

        for key, value in update_data.items():
            if value is not None:
                setattr(device, key, value)

        # The 'last_seen' field is updated automatically via the model's onupdate hook
        await self.session.commit()
        await self.session.refresh(device)
        return device

    async def update_device_status(
        self, device_id: PyUUID, user_id: PyUUID, new_status: DeviceStatus
    ) -> Device:
        """
        Updates only the status of a specific device.
        """
        device = await self.get_device(device_id, user_id=user_id)
        if not device:
            raise InvalidRequestException(f"Device with ID {device_id} not found.")

        device.status = new_status.value
        device.last_seen = datetime.now(timezone.utc)
        # The 'last_seen' field will also be updated automatically
        await self.session.commit()
        await self.session.refresh(device)
        return device

    async def delete_device(self, device_id: PyUUID, user_id: PyUUID) -> Device:
        """
        Marks a device as soft-deleted.
        """
        device = await self.get_device(device_id, user_id=user_id)
        if not device:
            raise InvalidRequestException(f"Device with ID {device_id} not found.")

        device.soft_delete()
        await self.session.commit()
        await self.session.refresh(device)
        return device


DeviceServiceDependency = Annotated[DeviceService, DeviceService.get_dependency()]
