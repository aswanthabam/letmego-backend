# apps/api/parking/__init__.py

# ONLY import models here (needed for registry)
from .models import (
    ParkingSlot,
    ParkingSlotStaff,
    ParkingSession,
    VehicleDue,
    ParkingVehicleType,
    PricingModel,
    SlotStatus,
    StaffRole,
    SessionStatus,
    PaymentStatus,
    DueStatus,
)

__all__ = [
    "ParkingSlot",
    "ParkingSlotStaff",
    "ParkingSession",
    "VehicleDue",
    "ParkingVehicleType",
    "PricingModel",
    "SlotStatus",
    "StaffRole",
    "SessionStatus",
    "PaymentStatus",
    "DueStatus",
]

# DO NOT import router here - it will be imported directly by your app loader