from fastapi import APIRouter, status
from typing import List, Optional
from uuid import UUID

from apps.api.auth.dependency import UserDependency
from apps.api.device.schema import (
    DeviceCreate,
    DeviceUpdate,
    DeviceStatusUpdate,
    DeviceResponse,
    DeviceStatus,
)
from apps.api.device.service import DeviceServiceDependency

router = APIRouter(prefix="/device", tags=["Devices"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    description="Register a new device.",
)
async def create_device_endpoint(
    device_data: DeviceCreate,
    device_service: DeviceServiceDependency,
    user: UserDependency,
) -> DeviceResponse:
    """
    Creates a new device record. A device token must be unique.
    """
    return await device_service.create_device(
        user_id=user.id, **device_data.model_dump()
    )


@router.get(
    "/get/{device_id}",
    description="Get a specific device by its UUID.",
)
async def get_device_endpoint(
    device_id: str,
    device_service: DeviceServiceDependency,
    user: UserDependency,
) -> DeviceResponse:
    """
    Retrieves the details of a single device using its unique ID.
    """
    return await device_service.get_device(
        device_id=device_id, user_id=user.id, update_status=True
    )


# @router.patch(
#     "/update/{device_id}",
#     response_model=DeviceResponse,
#     description="Update a device's details.",
# )
# async def update_device_endpoint(
#     device_id: UUID,
#     device_data: DeviceUpdate,
#     device_service: DeviceServiceDependency,
#     user: UserDependency,
# ):
#     """
#     Updates one or more fields of an existing device.
#     """
#     # model_dump(exclude_unset=True) ensures we only send provided values to the service
#     update_data = device_data.model_dump(exclude_unset=True)
#     return await device_service.update_device(
#         device_id=device_id, user_id=user.id, **update_data
#     )


@router.patch(
    "/status/{device_id}",
    response_model=DeviceResponse,
    description="Update a device's status.",
)
async def update_device_status_endpoint(
    device_id: UUID,
    status_data: DeviceStatusUpdate,
    device_service: DeviceServiceDependency,
    user: UserDependency,
):
    """
    Updates the status of a specific device (e.g., to ACTIVE or INACTIVE).
    """
    return await device_service.update_device_status(
        device_id=device_id, new_status=status_data.status, user_id=user.id
    )


# @router.delete(
#     "/delete/{device_id}",
#     status_code=status.HTTP_200_OK,
#     response_model=DeviceResponse,
#     description="Soft-delete a device.",
# )
# async def delete_device_endpoint(
#     device_id: UUID,
#     device_service: DeviceServiceDependency,
#     user: UserDependency,
# ):
#     """
#     Marks a device as deleted without permanently removing it from the database.
#     """
#     return await device_service.delete_device(device_id=device_id, user_id=user.id)
