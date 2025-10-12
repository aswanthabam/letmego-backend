# apps/api/apartment/schema.py

from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import Field

from avcfastapi.core.fastapi.response.models import CustomBaseModel


# ===== Apartment Schemas =====
class ApartmentBase(CustomBaseModel):
    """Base schema for Apartment"""
    name: str = Field(..., min_length=1, max_length=200, description="Apartment complex name")
    address: str = Field(..., min_length=1, max_length=500, description="Apartment address")
    description: Optional[str] = Field(None, description="Apartment description")


class ApartmentCreate(ApartmentBase):
    """Schema for creating a new apartment (by super admin)"""
    admin_id: UUID = Field(..., description="UUID of the user who will be the apartment admin")


class ApartmentUpdate(CustomBaseModel):
    """Schema for updating an apartment"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    address: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    admin_id: Optional[UUID] = Field(None, description="Change apartment admin")


class ApartmentResponse(ApartmentBase):
    """Schema for apartment response"""
    id: UUID
    admin_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===== Permitted Vehicle Schemas =====
class PermittedVehicleBase(CustomBaseModel):
    """Base schema for permitted vehicle"""
    vehicle_id: UUID = Field(..., description="UUID of the vehicle")
    notes: Optional[str] = Field(None, max_length=500, description="Additional notes")
    parking_spot: Optional[str] = Field(None, max_length=50, description="Parking spot identifier")


class PermittedVehicleCreate(PermittedVehicleBase):
    """Schema for adding a permitted vehicle"""
    pass


class PermittedVehicleUpdate(CustomBaseModel):
    """Schema for updating permitted vehicle details"""
    notes: Optional[str] = Field(None, max_length=500)
    parking_spot: Optional[str] = Field(None, max_length=50)


class PermittedVehicleResponse(CustomBaseModel):
    """Schema for permitted vehicle response"""
    id: UUID
    apartment_id: UUID
    vehicle_id: UUID
    notes: Optional[str]
    parking_spot: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VehiclePermissionCheckResponse(CustomBaseModel):
    """Schema for vehicle permission check response"""
    is_permitted: bool
    apartment_id: Optional[UUID] = None
    apartment_name: Optional[str] = None
    parking_spot: Optional[str] = None
    notes: Optional[str] = None
