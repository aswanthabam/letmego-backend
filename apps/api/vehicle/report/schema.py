from typing import List, Optional
from uuid import UUID
from datetime import datetime
from enum import Enum  # Import Enum

from pydantic import BaseModel, Field


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


class VehicleReportMarkResolved(BaseModel):
    """
    Schema for marking a vehicle report as resolved or unresolved by the reporter.
    """

    is_resolved: bool = Field(
        ..., description="True to mark as resolved, False to mark as unresolved."
    )
    notes: Optional[str] = Field(
        None, description="Optional notes regarding the resolution status change."
    )


# --- Response Schemas ---


class UserMin(BaseModel):
    id: UUID
    fullname: str
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


class VehicleReportDetail(BaseModel):
    """
    Schema for reading a single vehicle report with details.
    """

    id: UUID
    report_number: int
    vehicle: VehicleDetail
    user_id: UUID
    notes: Optional[str]
    current_status: str
    created_at: datetime
    updated_at: datetime
    images: List[VehicleReportImageMin] = []
    status_logs: List[VehicleReportStatusLogMin] = []

    class Config:
        from_attributes = True


class VehicleReportMin(BaseModel):
    id: UUID
    report_number: int
    vehicle: VehicleDetail
    reporter: UserMin
    current_status: str
    notes: Optional[str] = None
    images: List[VehicleReportImageMin] = []
    created_at: datetime
    updated_at: datetime
