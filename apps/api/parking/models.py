# apps/api/parking/models.py

from sqlalchemy import Column, String, Float, Numeric, Enum as SQLEnum, ForeignKey, UUID, UniqueConstraint
import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
import enum

from avcfastapi.core.database.sqlalchamey.base import AbstractSQLModel
from avcfastapi.core.database.sqlalchamey.mixins import SoftDeleteMixin, TimestampsMixin
from avcfastapi.core.database.sqlalchamey.fields import TZAwareDateTime


# ===== Enums =====

class ParkingVehicleType(str, enum.Enum):
    """Simplified vehicle types for parking capacity"""
    CAR = "car"
    BIKE = "bike"
    TRUCK = "truck"


class PricingModel(str, enum.Enum):
    """Pricing models for parking slots"""
    FREE = "free"
    FIXED = "fixed"  # One-time fixed fee
    HOURLY = "hourly"  # Base fee + incremental per hour


class PaymentTiming(str, enum.Enum):
    """When payment is collected"""
    UPFRONT = "upfront"  # Pay on entry
    ON_EXIT = "on_exit"  # Pay on exit


class PaymentMode(str, enum.Enum):
    """Payment mode for transactions"""
    CASH = "cash"
    UPI = "upi"
    CARD = "card"
    OTHER = "other"


class SlotStatus(str, enum.Enum):
    """Parking slot verification status"""
    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    INACTIVE = "inactive"
    REJECTED = "rejected"


class StaffRole(str, enum.Enum):
    """Role of staff member in parking slot"""
    OWNER = "owner"
    STAFF = "staff"
    VOLUNTEER = "volunteer"


class SessionStatus(str, enum.Enum):
    """Status of parking session"""
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    ESCAPED = "escaped"


class PaymentStatus(str, enum.Enum):
    """Payment status for session"""
    PENDING = "pending"
    PAID = "paid"
    PARTIAL = "partial"


class DueStatus(str, enum.Enum):
    """Status of vehicle due"""
    PENDING = "pending"
    PAID = "paid"
    WRITTEN_OFF = "written_off"


# ===== Models =====

class ParkingSlot(AbstractSQLModel, SoftDeleteMixin, TimestampsMixin):
    """
    Parking slot created by users and verified by admin.
    Stores location, capacity, and pricing configuration.
    """
    __tablename__ = "parking_slots"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        default=sa.text("gen_random_uuid()"),
    )
    owner_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    name = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)
    location = Column(String(500), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # Capacity stored as JSON: {"car": 20, "bike": 10, "truck": 5}
    capacity = Column(
        JSONB,
        nullable=False,
        comment="Vehicle type capacity mapping"
    )
    
    # Pricing configuration
    pricing_model = Column(
        String(20),
        nullable=False,
        default=PricingModel.FREE.value
    )
    
    # Pricing config stored as JSON based on model:
    # FREE: {}
    # FIXED: {"car": 50, "bike": 20, "truck": 100}
    # HOURLY: {"car": {"base": 30, "base_hours": 2, "incremental": 10}, ...}
    pricing_config = Column(
        JSONB,
        nullable=True,
        comment="Pricing configuration based on pricing_model"
    )
    
    payment_timing = Column(
        String(20),
        nullable=False,
        default=PaymentTiming.ON_EXIT.value
    )
    
    status = Column(
        String(30),
        nullable=False,
        default=SlotStatus.PENDING_VERIFICATION.value,
        index=True
    )
    
    # Admin verification details
    verified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    verified_at = Column(TZAwareDateTime(timezone=True), nullable=True)
    rejection_reason = Column(String(500), nullable=True)

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id])
    verifier = relationship("User", foreign_keys=[verified_by])
    staff = relationship("ParkingSlotStaff", back_populates="slot", cascade="all, delete-orphan")
    sessions = relationship("ParkingSession", back_populates="slot", cascade="all, delete-orphan")


class ParkingSlotStaff(AbstractSQLModel, TimestampsMixin):
    """
    Links users as staff/volunteers to specific parking slots.
    Owner is automatically added on slot creation.
    """
    __tablename__ = "parking_slot_staff"
    __table_args__ = (
        UniqueConstraint('slot_id', 'user_id', name='uq_slot_staff'),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        default=sa.text("gen_random_uuid()"),
    )
    slot_id = Column(
        UUID(as_uuid=True),
        ForeignKey("parking_slots.id"),
        nullable=False,
        index=True
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    role = Column(
        String(20),
        nullable=False,
        default=StaffRole.STAFF.value
    )

    # Relationships
    slot = relationship("ParkingSlot", back_populates="staff")
    user = relationship("User")


class ParkingSession(AbstractSQLModel, TimestampsMixin):
    """
    Tracks every vehicle check-in and check-out transaction.
    Stores calculated fees and payment status.
    
    NEW: Links to vehicle owner when vehicle_number matches registered vehicle.
    """
    __tablename__ = "parking_sessions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        default=sa.text("gen_random_uuid()"),
    )
    slot_id = Column(
        UUID(as_uuid=True),
        ForeignKey("parking_slots.id"),
        nullable=False,
        index=True
    )
    vehicle_number = Column(
        String(20),
        nullable=False,
        index=True,
        comment="Vehicle registration number"
    )
    vehicle_type = Column(
        String(20),
        nullable=False
    )
    
    # NEW: Link to vehicle owner (optional - only if vehicle is registered)
    vehicle_owner_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
        comment="Owner of the vehicle (if registered in system)"
    )
    checked_in_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False
    )
    checked_out_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )
    
    check_in_time = Column(
        TZAwareDateTime(timezone=True),
        nullable=False,
        index=True
    )
    check_out_time = Column(
        TZAwareDateTime(timezone=True),
        nullable=True
    )
    
    status = Column(
        String(20),
        nullable=False,
        default=SessionStatus.CHECKED_IN.value,
        index=True
    )
    
    calculated_fee = Column(
        Numeric(10, 2),
        nullable=False,
        default=0,
        comment="Calculated parking fee based on duration"
    )
    collected_fee = Column(
        Numeric(10, 2),
        nullable=True,
        comment="Actual amount collected from customer"
    )
    payment_mode = Column(
        String(20),
        nullable=True,
        comment="Mode of payment: cash, upi, card, other"
    )
    payment_status = Column(
        String(20),
        nullable=False,
        default=PaymentStatus.PENDING.value
    )
    
    notes = Column(String(500), nullable=True)

    # Relationships
    slot = relationship("ParkingSlot", back_populates="sessions")
    check_in_staff = relationship("User", foreign_keys=[checked_in_by])
    check_out_staff = relationship("User", foreign_keys=[checked_out_by])
    vehicle_owner = relationship("User", foreign_keys=[vehicle_owner_id])  # NEW
    due = relationship("VehicleDue", back_populates="session", uselist=False, foreign_keys="[VehicleDue.session_id]")


class VehicleDue(AbstractSQLModel, TimestampsMixin):
    """
    Tracks vehicles that escaped without paying.
    Links to slot owner (not specific slot) for cross-slot tracking.
    """
    __tablename__ = "vehicle_dues"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        default=sa.text("gen_random_uuid()"),
    )
    vehicle_number = Column(
        String(20),
        nullable=False,
        index=True,  # Critical for due checking on check-in
        comment="Vehicle registration number with unpaid dues"
    )
    slot_owner_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        comment="Owner of parking slot (for cross-slot tracking)"
    )
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("parking_sessions.id"),
        nullable=False,
        unique=True,
        comment="Original escaped session"
    )
    
    # Financial tracking
    due_amount = Column(
        Numeric(10, 2),
        nullable=False,
        comment="Original unpaid amount"
    )
    paid_amount = Column(
        Numeric(10, 2),
        nullable=False,
        default=0,
        comment="Amount paid towards this due"
    )
    
    status = Column(
        String(20),
        nullable=False,
        default=DueStatus.PENDING.value,
        index=True
    )
    
    # Payment tracking
    paid_at = Column(TZAwareDateTime(timezone=True), nullable=True)
    paid_by_staff = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        comment="Staff who collected the payment"
    )
    payment_session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("parking_sessions.id"),
        nullable=True,
        comment="Session during which due was paid"
    )
    payment_mode = Column(
        String(20),
        nullable=True,
        comment="Mode of payment: cash, upi, card, other"
    )
    
    notes = Column(String(500), nullable=True)

    # Relationships
    owner = relationship("User", foreign_keys=[slot_owner_id])
    session = relationship("ParkingSession", foreign_keys=[session_id], back_populates="due")
    payment_staff = relationship("User", foreign_keys=[paid_by_staff])
    payment_session = relationship("ParkingSession", foreign_keys=[payment_session_id])