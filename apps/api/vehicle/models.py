# apps/vehicle/models.py

from core.storage.fields import S3ImageField
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, UUID, Enum
from sqlalchemy.orm import relationship
import sqlalchemy as sa
import enum

from core.db.base import AbstractSQLModel
from core.db.mixins import SoftDeleteMixin, TimestampsMixin


# -------------------------
# Vehicle Type Enum
# -------------------------
class VehicleType(enum.Enum):
    CAR = "Car"
    MOTORCYCLE = "Motorcycle"
    TRUCK = "Truck"
    BUS = "Bus"
    VAN = "Van"
    SUV = "SUV"
    PICKUP_TRUCK = "Pickup Truck"
    SCOOTER = "Scooter"
    BICYCLE = "Bicycle"
    TRAILER = "Trailer"
    RICKSHAW = "Rickshaw"
    AUTO_RICKSHAW = "Auto Rickshaw"
    TRACTOR = "Tractor"
    AMBULANCE = "Ambulance"
    FIRE_TRUCK = "Fire Truck"
    POLICE_VEHICLE = "Police Vehicle"
    TAXI = "Taxi"
    OTHER = "Other"

    @classmethod
    def choices(cls):
        """Return a list of (value, display_name) tuples"""
        return [(member.value, member.value) for member in cls]


# -------------------------
# 1. Vehicle Model
# -------------------------
class Vehicle(AbstractSQLModel, SoftDeleteMixin, TimestampsMixin):
    __tablename__ = "vehicles"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        default=sa.text("gen_random_uuid()"),
    )
    vehicle_number = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=True)
    vehicle_type = Column(Enum(VehicleType), nullable=True)
    brand = Column(String(50), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    image = Column(
        S3ImageField(
            upload_to="vehicle/images/",
            variations={
                "thumbnail": {"width": 150, "height": 150},
                "medium": {"width": 500, "height": 500},
                "large": {"width": 800, "height": 800},
            },
        ),
        nullable=True,
    )
    is_verified = Column(Boolean, default=False)

    owner = relationship("User", back_populates="vehicles")
    reports = relationship("VehicleReport", back_populates="vehicle")