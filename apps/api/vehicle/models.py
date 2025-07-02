from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, UUID
from sqlalchemy.orm import relationship
import sqlalchemy as sa

from core.db.base import AbstractSQLModel
from core.db.mixins import SoftDeleteMixin, TimestampsMixin


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
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    is_verified = Column(Boolean, default=False)

    owner = relationship("User", back_populates="vehicles")
    reports = relationship("VehicleReport", back_populates="vehicle")
