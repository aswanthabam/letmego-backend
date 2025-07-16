from datetime import datetime
from enum import Enum
import enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DeviceStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"


class DeviceStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    UNINSTALLED = "UNINSTALLED"


class DeviceBase(BaseModel):
    """Base schema with common fields for a device."""

    platform: str = Field(
        ..., description="Platform of the device (e.g., 'ios', 'android')."
    )
    device_model: Optional[str] = None
    os_version: Optional[str] = None
    app_version: Optional[str] = None
    language_code: Optional[str] = "en"
    push_enabled: Optional[str] = "UNKNOWN"

    class Config:
        from_attributes = True


class DeviceCreate(DeviceBase):
    """Schema for creating a new device."""

    device_token: str = Field(
        ..., description="The unique push notification token for the device."
    )


class DeviceUpdate(BaseModel):
    """Schema for updating a device. All fields are optional."""

    device_token: Optional[str] = None
    device_model: Optional[str] = None
    platform: Optional[str] = None
    os_version: Optional[str] = None
    app_version: Optional[str] = None
    language_code: Optional[str] = None
    push_enabled: Optional[str] = None


class DeviceStatusUpdate(BaseModel):
    """Schema for updating only the device's status."""

    status: DeviceStatus = Field(..., description="The new status for the device.")


class DeviceResponse(DeviceBase):
    """Schema for representing a device in API responses."""

    id: UUID
    user_id: Optional[UUID] = None
    device_token: str
    status: str
    last_seen: datetime
    created_at: datetime
    updated_at: datetime
