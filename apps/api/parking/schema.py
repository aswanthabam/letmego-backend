# apps/api/parking/schema.py

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


# ===== Pricing & Capacity Sub-Schemas =====

class CapacityConfig(CustomBaseModel):
    car: int = Field(0, ge=0, description="Parking capacity for cars")
    bike: int = Field(0, ge=0, description="Parking capacity for bikes")
    truck: int = Field(0, ge=0, description="Parking capacity for trucks")


class HourlyTierConfig(CustomBaseModel):
    base: float = Field(..., ge=0, description="Base fee amount")
    base_hours: float = Field(..., gt=0, description="Number of hours covered by base fee")
    incremental: float = Field(..., ge=0, description="Fee per additional hour")


class HourlyPricingConfig(CustomBaseModel):
    car: Optional[HourlyTierConfig] = None
    bike: Optional[HourlyTierConfig] = None
    truck: Optional[HourlyTierConfig] = None


class FixedPricingConfig(CustomBaseModel):
    car: Optional[float] = Field(None, ge=0)
    bike: Optional[float] = Field(None, ge=0)
    truck: Optional[float] = Field(None, ge=0)


# ===== Parking Slot Schemas =====

class ParkingSlotCreate(CustomBaseModel):
    """Schema for creating a new parking slot"""
    name: str = Field(..., min_length=1, max_length=200, description="Parking slot name")
    description: Optional[str] = Field(None, max_length=500, description="Slot description")
    location: str = Field(..., min_length=1, max_length=500, description="Physical address")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude")
    
    # NEW: Multi-tenant Organization ID
    organization_id: Optional[UUID] = Field(None, description="The B2B tenant organization that owns this slot")
    
    capacity: CapacityConfig = Field(..., description="Capacity by vehicle type")
    
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

    @field_validator('pricing_config')
    def validate_pricing_config(cls, v, info):
        """Validate pricing config matches pricing model using explicit schemas"""
        if not v:
            return v
            
        model = info.data.get('pricing_model')
        
        if model == PricingModel.FREE:
            return {}
            
        if model == PricingModel.FIXED:
            # Pydantic will validate the dict layout
            FixedPricingConfig(**v)
            return v
            
        if model == PricingModel.HOURLY:
            HourlyPricingConfig(**v)
            return v
            
        return v


class ParkingSlotUpdate(CustomBaseModel):
    """Schema for updating parking slot (owner only, when not active)"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, min_length=1, max_length=500)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    
    capacity: Optional[CapacityConfig] = None
    
    pricing_model: Optional[PricingModel] = None
    pricing_config: Optional[Dict] = None
    payment_timing: Optional[PaymentTiming] = None

    @field_validator('pricing_config')
    def validate_pricing_config(cls, v, info):
        """Validate pricing config matches pricing model when both are provided"""
        if not v:
            return v
        
        model = info.data.get('pricing_model')
        if not model:
            return v
        
        if model == PricingModel.FREE:
            return {}
        
        if model == PricingModel.FIXED:
            FixedPricingConfig(**v)
            return v
        
        if model == PricingModel.HOURLY:
            HourlyPricingConfig(**v)
            return v
        
        return v


class ParkingSlotResponse(CustomBaseModel):
    """Schema for parking slot response"""
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
    """Schema for adding staff to parking slot"""
    user_id: UUID = Field(..., description="User ID to add as staff")
    role: StaffRole = Field(StaffRole.STAFF, description="Role for this staff member")


class StaffAddByEmail(CustomBaseModel):
    """NEW: Schema for adding staff by email"""
    email: EmailStr = Field(..., description="Email address of user to add as staff")
    role: StaffRole = Field(StaffRole.STAFF, description="Role for this staff member")


class StaffResponse(CustomBaseModel):
    """Schema for staff member response"""
    id: UUID
    slot_id: UUID
    user_id: UUID
    role: StaffRole
    email: Optional[str] = None  # NEW: User email
    name: Optional[str] = None   # NEW: User name
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Parking Session Schemas =====

class SessionCheckIn(CustomBaseModel):
    """Schema for checking in a vehicle"""
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


class SessionCalculateFee(CustomBaseModel):
    """Schema for calculating parking fee before checkout"""
    pass  # No fields needed, just triggers calculation


class SessionCheckOut(CustomBaseModel):
    """Schema for checking out a vehicle and collecting payment"""
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
    """Schema for parking session response"""
    id: UUID
    slot_id: UUID
    vehicle_number: str
    vehicle_type: ParkingVehicleType
    vehicle_owner_id: Optional[UUID] = None  # NEW
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

    class Config:
        from_attributes = True


class SessionFeeCalculation(CustomBaseModel):
    """Schema for fee calculation response"""
    session_id: UUID
    vehicle_number: str
    vehicle_type: ParkingVehicleType
    check_in_time: datetime
    current_time: datetime
    duration_hours: float
    calculated_fee: Decimal
    pricing_details: dict


class SessionWithDueAlert(SessionResponse):
    """Session response with due alert information"""
    has_outstanding_due: bool = Field(False, description="Vehicle has unpaid dues")
    due_amount: Optional[Decimal] = Field(None, description="Outstanding due amount")
    due_id: Optional[UUID] = Field(None, description="Due record ID")


# ===== NEW: Vehicle Transaction History Schemas =====

class SlotBasicInfo(CustomBaseModel):
    """Basic parking slot info for transaction history"""
    id: UUID
    name: str
    location: str
    pricing_model: PricingModel

    class Config:
        from_attributes = True


class TransactionHistoryItem(CustomBaseModel):
    """Individual transaction in vehicle history"""
    id: UUID
    slot: SlotBasicInfo
    vehicle_number: str
    vehicle_type: ParkingVehicleType
    check_in_time: datetime
    check_out_time: Optional[datetime]
    status: SessionStatus
    calculated_fee: Decimal
    collected_fee: Optional[Decimal]
    payment_mode: Optional[str]
    payment_status: PaymentStatus
    is_owned_by_user: bool = Field(..., description="True if this vehicle belongs to requesting user")
    
    class Config:
        from_attributes = True


class VehicleTransactionHistory(CustomBaseModel):
    """Complete transaction history for a vehicle"""
    vehicle_number: str
    is_registered: bool = Field(..., description="True if vehicle is registered in system")
    total_sessions: int
    total_spent: Decimal
    active_sessions: int
    outstanding_dues: Decimal
    transactions: List[TransactionHistoryItem]


class MyVehiclesHistory(CustomBaseModel):
    """Transaction history for all vehicles owned by user"""
    total_vehicles: int
    total_sessions: int
    total_spent: Decimal
    outstanding_dues: Decimal
    vehicles: List[Dict]  # List of vehicle summaries


# ===== Vehicle Due Schemas =====

class DueCollect(CustomBaseModel):
    """Schema for collecting payment on a due"""
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
    """Schema for vehicle due response"""
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

    class Config:
        from_attributes = True


# ===== Analytics Schemas =====

class DailyRevenue(CustomBaseModel):
    """Daily revenue breakdown by staff"""
    staff_id: UUID
    staff_name: str
    total_sessions: int
    total_collected: Decimal


class OwnerAnalytics(CustomBaseModel):
    """Analytics for parking slot owner"""
    slot_id: UUID
    slot_name: str
    date_range: Dict[str, datetime]
    total_sessions: int
    total_revenue: Decimal
    revenue_by_staff: list[DailyRevenue]
    total_dues: Decimal
    active_sessions: int


class AdminAnalytics(CustomBaseModel):
    """Master analytics for super admin"""
    date_range: Dict[str, datetime]
    total_slots: int
    active_slots: int
    total_revenue: Decimal
    total_sessions: int
    total_outstanding_dues: Decimal
    revenue_by_slot: list[Dict]


# ===== Admin Verification Schemas =====

class SlotVerification(CustomBaseModel):
    """Schema for admin to verify/reject slot"""
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


# ===== Public Nearby Slots Schemas =====

class NearbySlotResponse(CustomBaseModel):
    """Schema for public nearby parking slot with availability"""
    id: UUID
    name: str
    description: Optional[str]
    location: str
    latitude: float
    longitude: float
    distance_km: float = Field(..., description="Distance from search location in kilometers")
    capacity: Dict[str, int]
    pricing_model: PricingModel
    pricing_config: Optional[Dict]
    payment_timing: PaymentTiming
    availability: Dict[str, int] = Field(..., description="Available spaces by vehicle type")
    occupancy_percentage: float = Field(..., description="Overall occupancy percentage")
    
    class Config:
        from_attributes = True