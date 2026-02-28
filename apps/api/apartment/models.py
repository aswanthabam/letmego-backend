# apps/api/apartment/models.py

from sqlalchemy import Column, String, Text, UUID, ForeignKey, UniqueConstraint
import sqlalchemy as sa
from sqlalchemy.orm import relationship

from avcfastapi.core.database.sqlalchamey.base import AbstractSQLModel
from avcfastapi.core.database.sqlalchamey.mixins import SoftDeleteMixin, TimestampsMixin


class Apartment(AbstractSQLModel, SoftDeleteMixin, TimestampsMixin):
    """
    Apartment Model for managing apartment complexes
    """
    __tablename__ = "apartments"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        default=sa.text("gen_random_uuid()"),
    )
    name = Column(String(200), nullable=False)
    address = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    admin_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )  # Reference to the apartment admin user
    
    # NEW: Multi-tenant Organization ID
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)

    # Relationships
    admin = relationship("User", foreign_keys=[admin_id])
    organization = relationship("Organization", foreign_keys=[organization_id])
    permitted_vehicles = relationship(
        "ApartmentPermittedVehicle",
        back_populates="apartment",
        cascade="all, delete-orphan"
    )


class ApartmentPermittedVehicle(AbstractSQLModel, SoftDeleteMixin, TimestampsMixin):
    """
    Model to track vehicles permitted in apartment parking
    """
    __tablename__ = "apartment_permitted_vehicles"
    __table_args__ = (
        UniqueConstraint(
            'apartment_id',
            'vehicle_id',
            name='uq_apartment_vehicle'
        ),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        default=sa.text("gen_random_uuid()"),
    )
    apartment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("apartments.id"),
        nullable=False,
        index=True
    )
    vehicle_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.id"),
        nullable=False,
        index=True
    )
    notes = Column(String(500), nullable=True)  # e.g., "Owner: John Doe, Unit 204"
    parking_spot = Column(String(50), nullable=True)  # Optional parking spot identifier

    # Relationships
    apartment = relationship("Apartment", back_populates="permitted_vehicles")
    vehicle = relationship("Vehicle")
