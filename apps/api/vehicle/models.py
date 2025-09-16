# apps/vehicle/models.py

from sqlalchemy import Column, Float, Numeric, String, Boolean, ForeignKey, UUID
from sqlalchemy.orm import relationship
import sqlalchemy as sa
import enum

from apps.storage import default_storage
from avcfastapi.core.database.sqlalchamey.base import AbstractSQLModel
from avcfastapi.core.database.sqlalchamey.mixins import SoftDeleteMixin, TimestampsMixin
from avcfastapi.core.storage.sqlalchemy.fields.imagefield import ImageField


class VehicleLocationVisibility(enum.Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    # INVITE_ONLY = "invite_only"


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
    fuel_type = Column(String(50), nullable=True)
    vehicle_type = Column(String(30), nullable=True)
    brand = Column(String(50), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    image = Column(
        ImageField(
            storage=default_storage,
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
    locations = relationship("VehicleLocation", back_populates="vehicle")

    @property
    def owner_name(self) -> str:
        if not self.owner:
            return "Unknown Owner"
        return self.owner.fullname


class VehicleLocation(AbstractSQLModel, SoftDeleteMixin, TimestampsMixin):
    __tablename__ = "vehicle_locations"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        default=sa.text("gen_random_uuid()"),
    )
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    latitude = Column(Float(), nullable=False)
    longitude = Column(Float(), nullable=False)
    notes = Column(String(255), nullable=True)
    image = Column(
        ImageField(
            storage=default_storage,
            upload_to="vehicle/location_images/",
            variations={
                "thumbnail": {"width": 150, "height": 150},
                "medium": {"width": 500, "height": 500},
                "large": {"width": 800, "height": 800},
            },
        ),
        nullable=True,
    )
    visibility = Column(
        String(20),
        default=VehicleLocationVisibility.PRIVATE.value,
        nullable=False,
    )

    vehicle = relationship("Vehicle", back_populates="locations")
    user = relationship("User", back_populates="vehicle_locations")
