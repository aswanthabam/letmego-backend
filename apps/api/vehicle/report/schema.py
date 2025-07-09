from typing import List, Optional
from uuid import UUID
from datetime import datetime
from enum import Enum  # Import Enum

from pydantic import BaseModel, Field

from apps.api.user.schema import UserPrivacyWrapper
from apps.context import get_current_user_id


# Enums for statuses
class ReportStatusEnum(str, Enum):
    ACTIVE = "active"
    OWNER_NOTIFIED = "owner_notified"
    OWNER_SEEN = "owner_seen"
    OWNER_RESPONDED = "owner_responded"
    OWNER_RESOLVED = "owner_resolved"
    OWNER_REJECTED = "owner_rejected"
    REPORTER_CLOSED = "reporter_closed"
    REPORTER_RESOLVED = "reporter_resolved"
    REPORTER_REJECTED = "reporter_rejected"
    SYSTEM_CLOSED = "system_closed"

    @property
    def message(self) -> str:
        VEHICLE_STATUS_MESSAGES = {
            "active": "Report has been submitted and is now active.",
            "owner_notified": "The vehicle owner has been notified about the report.",
            "owner_seen": "The vehicle owner has seen the report.",
            "owner_responded": "The vehicle owner has responded to the report.",
            "owner_resolved": "The vehicle owner has resolved the issue mentioned in the report.",
            "owner_rejected": "The vehicle owner has rejected the claims in the report.",
            "reporter_resolved": "Reporter have marked this report as resolved.",
            "reporter_rejected": "Reporter have rejected the owner's response.",
            "reporter_closed": "Reporter have closed the report.",
            "system_closed": "The system has automatically closed this report due to inactivity.",
        }
        return VEHICLE_STATUS_MESSAGES[self.value]

    @property
    def is_closed(self) -> bool:
        CLOSED_STATUSES = {
            "reporter_closed",
            "reporter_resolved",
            "reporter_rejected",
            "system_closed",
            "owner_resolved",
            "owner_rejected",
        }
        return self.value in CLOSED_STATUSES


class VehicleReportPrivacyWrapper(BaseModel):
    """
    Base wrapper for vehicle report privacy.
    This will handle the privacy preferences of the user.
    """

    def model_post_init(self, context):
        viewer_id = get_current_user_id()
        has_perm = viewer_id == self.id
        is_anonymous = self.is_anonymous if hasattr(self, "is_anonymous") else False

        if hasattr(self, "reporter"):
            if not has_perm and is_anonymous:
                self.reporter.fullname = "Anonymous User"
                self.reporter.email = "xxxxxxxxxx"
                self.reporter.phone_number = "xxxxxxxxxx"
                self.reporter.profile_picture = None
                self.reporter.company_name = "xxxxxxxxxx"


class UserMin(UserPrivacyWrapper):
    id: UUID
    fullname: str | None = None
    email: str | None = None
    profile_picture: Optional[dict] = None
    company_name: Optional[str] = None


class VehicleDetail(BaseModel):
    """
    Schema for reading vehicle details.
    """

    id: UUID
    vehicle_number: str
    vehicle_type: str
    brand: Optional[str] = None
    image: Optional[dict] = None
    owner: UserMin | None = None

    class Config:
        from_attributes = True


class VehicleReportImageMin(BaseModel):
    """
    Schema for reading vehicle report images.
    """

    id: UUID
    image: dict

    class Config:
        from_attributes = True


class VehicleReportStatusLogMin(BaseModel):
    """
    Schema for reading vehicle report status logs.
    """

    id: UUID
    user_id: UUID
    status: str
    notes: Optional[str]
    data: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


class VehicleReportDetail(VehicleReportPrivacyWrapper):
    """
    Schema for reading a single vehicle report with details.
    """

    id: UUID
    report_number: int
    vehicle: VehicleDetail
    notes: Optional[str]
    current_status: str
    is_closed: bool
    is_anonymous: bool
    reporter: UserMin
    created_at: datetime
    updated_at: datetime
    images: List[VehicleReportImageMin] = []
    status_logs: List[VehicleReportStatusLogMin] = []

    class Config:
        from_attributes = True


class VehicleReportMin(VehicleReportPrivacyWrapper):
    id: UUID
    report_number: int
    vehicle: VehicleDetail
    reporter: UserMin
    current_status: str
    is_closed: bool
    is_anonymous: bool
    notes: Optional[str] = None
    images: List[VehicleReportImageMin] = []
    created_at: datetime
    updated_at: datetime
