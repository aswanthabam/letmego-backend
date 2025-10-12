# apps/api/shop/schema.py

from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import Field, EmailStr

from avcfastapi.core.fastapi.response.models import CustomBaseModel


class ShopBase(CustomBaseModel):
    """Base schema for Shop with common fields"""
    name: str = Field(..., min_length=1, max_length=200, description="Shop name")
    description: Optional[str] = Field(None, description="Shop description")
    address: Optional[str] = Field(None, max_length=500, description="Shop address")
    latitude: float = Field(..., ge=-90, le=90, description="Shop latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Shop longitude")
    phone_number: Optional[str] = Field(None, max_length=20, description="Contact phone number")
    email: Optional[EmailStr] = Field(None, description="Contact email")
    website: Optional[str] = Field(None, max_length=200, description="Shop website URL")
    category: Optional[str] = Field(None, max_length=100, description="Shop category")
    operating_hours: Optional[str] = Field(None, max_length=200, description="Operating hours")
    is_active: bool = Field(True, description="Whether the shop is active")


class ShopCreate(ShopBase):
    """Schema for creating a new shop"""
    pass


class ShopUpdate(CustomBaseModel):
    """Schema for updating an existing shop (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    address: Optional[str] = Field(None, max_length=500)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    phone_number: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    website: Optional[str] = Field(None, max_length=200)
    category: Optional[str] = Field(None, max_length=100)
    operating_hours: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None


class ShopResponse(ShopBase):
    """Schema for shop response"""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
