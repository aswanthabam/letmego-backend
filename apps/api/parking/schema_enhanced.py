# apps/api/parking/schema_enhanced.py

"""
Enhanced schemas with explicit role context indicators.

These schemas make it clear which operations require which roles:
- Owner operations: marked with [OWNER]
- Staff operations: marked with [STAFF]
- Customer operations: marked with [CUSTOMER]
"""

from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, List
from decimal import Decimal
from pydantic import Field, field_validator, EmailStr

from apps.api.parking.models import (
    ParkingVehicleType,
    PricingModel,
    PaymentTiming,
    SlotStatus,
    StaffRole,
    SessionStatus,
    PaymentStatus,
    DueStatus
)
from avcfastapi.core.fastapi.response.models import CustomBaseModel


# ===== Role Context Response =====

class UserRoleInSlot(CustomBaseModel):
    """Information about user's role in a specific slot"""
    slot_id: UUID
    slot_name: str
    role: StaffRole
    is_owner: bool
    can_manage_staff: bool
    can_check_in_out: bool
    can_collect_dues: bool
    can_view_analytics: bool


class MyWorkplacesResponse(CustomBaseModel):
    """
    Summary of all parking slots where user has access.
    Separates owned vs staffed slots for clarity.
    """
    total_slots: int = Field(..., description="Total slots user has access to")
    
    owned_slots: List[Dict] = Field(
        ...,
        description="Slots where user is the owner"
    )
    
    staff_slots: List[Dict] = Field(
        ...,
        description="Slots where user is staff/volunteer (not owner)"
    )
    
    role_summary: Dict = Field(
        ...,
        description="Summary of role distribution",
        example={
            "as_owner": 2,
            "as_staff": 5,
            "as_volunteer": 1
        }
    )


# ===== Parking Slot Schemas =====

class ParkingSlotCreate(CustomBaseModel):
    """
    [OWNER] Create a new parking slot.
    Creates you as the owner automatically.
    """
    name: str = Field(..., min_length=1, max_length=200, description="Parking slot name")
    description: Optional[str] = Field(None, max_length=500, description="Slot description")
    location: str = Field(..., min_length=1, max_length=500, description="Physical address")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude")
    capacity: Dict[str, int] = Field(
        ...,
        description="Capacity by vehicle type",
        example={"car": 20, "bike": 10, "truck": 5}
    )
    pricing_model: PricingModel = Field(..., description="Pricing model to use")
    pricing_config: Optional[Dict] = Field(
        None,
        description="Pricing configuration based on model",
        example={"car": {"base": 30, "base_hours": 2, "incremental": 10}}
    )
    payment_timing: PaymentTiming = Field(
        PaymentTiming.ON_EXIT,
        description="When payment is collected"
    )

    @field_validator('capacity')
    def validate_capacity(cls, v):
        """Validate capacity has valid vehicle types and positive values"""
        valid_types = {vt.value for vt in ParkingVehicleType}
        for vehicle_type, count in v.items():
            if vehicle_type not in valid_types:
                raise ValueError(f"Invalid vehicle type: {vehicle_type}. Must be one of {valid_types}")
            if count < 0:
                raise ValueError(f"Capacity for {vehicle_type} must be non-negative")
        return v


class ParkingSlotUpdate(CustomBaseModel):
    """
    [OWNER] Update parking slot configuration.
    Only available when slot is not ACTIVE.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, min_length=1, max_length=500)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    capacity: Optional[Dict[str, int]] = None
    pricing_model: Optional[PricingModel] = None
    pricing_config: Optional[Dict] = None
    payment_timing: Optional[PaymentTiming] = None


class ParkingSlotResponse(CustomBaseModel):
    """Response with parking slot information"""
    id: UUID
    owner_id: UUID
    name: str
    description: Optional[str]
    location: str
    latitude: float
    longitude: float
    capacity: Dict[str, int]
    pricing_model: PricingModel
    pricing_config: Optional[Dict]
    payment_timing: PaymentTiming
    status: SlotStatus
    verified_by: Optional[UUID]
    verified_at: Optional[datetime]
    rejection_reason: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    # Optional: User's role in this slot (populated for authenticated requests)
    my_role: Optional[StaffRole] = Field(
        None,
        description="Your role in this slot (if you have access)"
    )

    class Config:
        from_attributes = True


class SlotAvailability(CustomBaseModel):
    """Real-time availability for a parking slot"""
    slot_id: UUID
    capacity: Dict[str, int]
    occupied: Dict[str, int]
    available: Dict[str, int]
    occupancy_percentage: float


# ===== Staff Management Schemas =====

class StaffAdd(CustomBaseModel):
    """
    [OWNER] Add staff member to your parking slot by UUID.
    Only available for ACTIVE slots.
    """
    user_id: UUID = Field(..., description="User ID to add as staff")
    role: StaffRole = Field(
        StaffRole.STAFF,
        description="Role for this staff member (STAFF or VOLUNTEER)"
    )
    
    @field_validator('role')
    def validate_role(cls, v):
        """Can't add someone as OWNER"""
        if v == StaffRole.OWNER:
            raise ValueError("Cannot assign OWNER role through this endpoint")
        return v


class StaffAddByEmail(CustomBaseModel):
    """
    [OWNER] Add staff member to your parking slot by email.
    User must exist in the system.
    """
    email: EmailStr = Field(..., description="Email address of user to add as staff")
    role: StaffRole = Field(
        StaffRole.STAFF,
        description="Role for this staff member (STAFF or VOLUNTEER)"
    )
    
    @field_validator('role')
    def validate_role(cls, v):
        """Can't add someone as OWNER"""
        if v == StaffRole.OWNER:
            raise ValueError("Cannot assign OWNER role through this endpoint")
        return v


class StaffResponse(CustomBaseModel):
    """Response with staff member information"""
    id: UUID
    slot_id: UUID
    user_id: UUID
    role: StaffRole
    email: Optional[str] = None
    name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class StaffListResponse(CustomBaseModel):
    """
    [OWNER] List of all staff members for a slot.
    Shows who can operate the slot.
    """
    slot_id: UUID
    slot_name: str
    total_staff: int
    staff_members: List[StaffResponse]


# ===== Parking Session Schemas =====

class SessionCheckIn(CustomBaseModel):
    """
    [STAFF] Check in a vehicle to the parking slot.
    Any staff member can do this.
    """
    vehicle_number: str = Field(
        ...,
        min_length=3,
        max_length=20,
        description="Vehicle registration number"
    )
    vehicle_type: ParkingVehicleType = Field(..., description="Type of vehicle")
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator('vehicle_number')
    def normalize_vehicle_number(cls, v):
        """Normalize vehicle number (remove special chars, uppercase)"""
        import re
        return re.sub(r"[^a-zA-Z0-9]", "", v).upper()


class SessionCheckOut(CustomBaseModel):
    """
    [STAFF] Check out a vehicle and collect payment.
    Any staff member can do this.
    """
    collected_fee: Decimal = Field(
        ...,
        ge=0,
        description="Actual amount collected from customer"
    )
    payment_mode: str = Field(
        ...,
        description="Payment mode: cash, upi, card, other"
    )
    notes: Optional[str] = Field(None, max_length=500)
    
    @field_validator('payment_mode')
    def validate_payment_mode(cls, v):
        """Validate payment mode"""
        from apps.api.parking.models import PaymentMode
        valid_modes = {mode.value for mode in PaymentMode}
        if v.lower() not in valid_modes:
            raise ValueError(f"Invalid payment mode. Must be one of: {valid_modes}")
        return v.lower()


class SessionResponse(CustomBaseModel):
    """Response with parking session information"""
    id: UUID
    slot_id: UUID
    vehicle_number: str
    vehicle_type: ParkingVehicleType
    vehicle_owner_id: Optional[UUID] = None
    checked_in_by: UUID
    checked_out_by: Optional[UUID]
    check_in_time: datetime
    check_out_time: Optional[datetime]
    status: SessionStatus
    calculated_fee: Decimal
    collected_fee: Optional[Decimal]
    payment_mode: Optional[str]
    payment_status: PaymentStatus
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    # Optional: Context info
    slot_name: Optional[str] = Field(None, description="Parking slot name")
    checked_in_by_name: Optional[str] = Field(None, description="Staff who checked in")
    checked_out_by_name: Optional[str] = Field(None, description="Staff who checked out")

    class Config:
        from_attributes = True


class SessionWithDueAlert(SessionResponse):
    """
    [STAFF] Session response with due alert.
    Shows if vehicle has outstanding dues.
    """
    has_outstanding_due: bool = Field(False, description="Vehicle has unpaid dues")
    due_amount: Optional[Decimal] = Field(None, description="Outstanding due amount")
    due_id: Optional[UUID] = Field(None, description="Due record ID")
    due_warning: Optional[str] = Field(
        None,
        description="Human-readable warning message"
    )


# ===== Vehicle Due Schemas =====

class DueCollect(CustomBaseModel):
    """
    [STAFF] Collect payment on an outstanding due.
    Any staff working for the slot owner can collect.
    """
    paid_amount: Decimal = Field(..., gt=0, description="Amount being paid")
    payment_mode: str = Field(
        ...,
        description="Payment mode: cash, upi, card, other"
    )
    payment_session_id: Optional[UUID] = Field(
        None,
        description="Session during which payment was collected"
    )
    notes: Optional[str] = Field(None, max_length=500)
    
    @field_validator('payment_mode')
    def validate_payment_mode(cls, v):
        """Validate payment mode"""
        from apps.api.parking.models import PaymentMode
        valid_modes = {mode.value for mode in PaymentMode}
        if v.lower() not in valid_modes:
            raise ValueError(f"Invalid payment mode. Must be one of: {valid_modes}")
        return v.lower()


class DueResponse(CustomBaseModel):
    """Response with vehicle due information"""
    id: UUID
    vehicle_number: str
    slot_owner_id: UUID
    session_id: UUID
    due_amount: Decimal
    paid_amount: Decimal
    status: DueStatus
    paid_at: Optional[datetime]
    paid_by_staff: Optional[UUID]
    payment_session_id: Optional[UUID]
    payment_mode: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    # Optional: Context info
    remaining_amount: Optional[Decimal] = Field(
        None,
        description="Remaining unpaid amount"
    )

    class Config:
        from_attributes = True


# ===== Analytics Schemas =====

class StaffPerformance(CustomBaseModel):
    """Performance metrics for a staff member"""
    staff_id: UUID
    staff_name: str
    role: StaffRole
    total_check_ins: int
    total_check_outs: int
    total_collected: Decimal
    dues_collected: Decimal


class SlotAnalytics(CustomBaseModel):
    """
    [OWNER] Analytics for your parking slot.
    Detailed revenue and performance metrics.
    """
    slot_id: UUID
    slot_name: str
    date_range: Dict[str, datetime]
    
    # Session metrics
    total_sessions: int
    active_sessions: int
    completed_sessions: int
    escaped_sessions: int
    
    # Financial metrics
    total_revenue: Decimal
    total_collected: Decimal
    total_escaped: Decimal
    outstanding_dues: Decimal
    
    # Staff performance
    staff_performance: List[StaffPerformance]
    
    # Occupancy metrics
    average_occupancy: float
    peak_hours: List[Dict]


# ===== Admin Verification Schemas =====

class SlotVerification(CustomBaseModel):
    """
    [ADMIN] Verify or reject a parking slot.
    Admin only operation.
    """
    status: SlotStatus = Field(
        ...,
        description="New status (ACTIVE or REJECTED)"
    )
    rejection_reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Required if status is REJECTED"
    )

    @field_validator('rejection_reason')
    def validate_rejection_reason(cls, v, info):
        """Require rejection reason if status is REJECTED"""
        status = info.data.get('status')
        if status == SlotStatus.REJECTED and not v:
            raise ValueError("rejection_reason is required when rejecting a slot")
        return v


# ===== Public/Customer Schemas =====

class NearbySlotResponse(CustomBaseModel):
    """
    [CUSTOMER] Public nearby parking slot information.
    No authentication required.
    """
    id: UUID
    name: str
    description: Optional[str]
    location: str
    latitude: float
    longitude: float
    distance_km: float = Field(..., description="Distance from your location")
    capacity: Dict[str, int]
    pricing_model: PricingModel
    pricing_config: Optional[Dict]
    payment_timing: PaymentTiming
    availability: Dict[str, int] = Field(..., description="Available spaces by vehicle type")
    occupancy_percentage: float
    
    class Config:
        from_attributes = True


class VehicleQuickLookup(CustomBaseModel):
    """
    [STAFF] Quick vehicle information for check-in.
    Shows if vehicle has dues or recent history.
    """
    vehicle_number: str
    is_registered: bool
    has_outstanding_dues: bool
    outstanding_due_amount: Decimal
    total_visits: int
    last_visit_date: Optional[datetime]
    recent_sessions: List[Dict] = Field(
        ...,
        description="Last 5 parking sessions"
    )