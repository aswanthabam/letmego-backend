import uuid
from pydantic import Field
from datetime import datetime
from uuid import UUID
from typing import Optional, List

from apps.api.user.schema import PrivacyPreference
from avcfastapi.core.fastapi.response.models import CustomBaseModel


class UserListResponse(CustomBaseModel):
    id: uuid.UUID = Field(...)
    uid: str = Field(...)
    email: str | None = Field(None)
    phone_number: str | None = Field(None)
    fullname: str | None = Field(None)
    email_verified: bool = Field(False)
    profile_picture: dict | None = Field(None)
    company_name: str | None = Field(None)
    privacy_preference: PrivacyPreference | None = Field(None)


# -------------------------
# Shared Base Schema
# -------------------------
class BaseSchema(CustomBaseModel):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# -------------------------
# VehicleReportStatusLog
# -------------------------
class VehicleReportStatusLogSchema(BaseSchema):
    report_id: UUID
    user_id: UUID
    status: str
    notes: Optional[str] = None
    data: Optional[dict] = None


# -------------------------
# VehicleReportImage
# -------------------------
class VehicleReportImageSchema(BaseSchema):
    report_id: UUID
    image: Optional[dict] = None  # Will serialize ImageField -> str (url/path)


# -------------------------
# VehicleReport
# -------------------------
class VehicleReportSchema(BaseSchema):
    report_number: int
    vehicle_id: UUID
    user_id: UUID
    notes: Optional[str] = None
    current_status: str
    is_anonymous: bool = False
    is_closed: bool = False
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    location: Optional[str] = None

    # Relations
    images: List[VehicleReportImageSchema] = []
    status_logs: List[VehicleReportStatusLogSchema] = []

    reporter: Optional[UserListResponse] = None  # property from model


# -------------------------
# Vehicle
# -------------------------
class VehicleSchema(BaseSchema):
    vehicle_number: str
    name: Optional[str] = None
    fuel_type: Optional[str] = None
    vehicle_type: Optional[str] = None
    brand: Optional[str] = None
    user_id: UUID
    image: Optional[dict] = None
    is_verified: bool = False

    # Relations
    owner: Optional[UserListResponse] = None
    # reports: List[VehicleReportSchema] = []


# -------------------------
# User
# -------------------------
class UserSchema(BaseSchema):
    uid: str
    fullname: str
    email: Optional[str] = None
    email_verified: bool = False
    phone_number: Optional[str] = None
    profile_picture: Optional[dict] = None
    company_name: Optional[str] = None
    privacy_preference: str = "public"

    # Relations
    # vehicles: List[VehicleSchema] = []
    # reports: List[VehicleReportSchema] = []


# -------------------------
# Annotated List Schemas
# -------------------------
class UserWithCountsSchema(CustomBaseModel):
    user: UserSchema
    total_vehicle_count: int
    total_reports_against_user: int

    class Config:
        from_attributes = True


class VehicleWithCountsSchema(CustomBaseModel):
    vehicle: VehicleSchema
    total_reports_against_user: int

    class Config:
        from_attributes = True
