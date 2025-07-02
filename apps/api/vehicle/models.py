from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from core.db.base import AbstractSQLModel
from core.db.mixins import SoftDeleteMixin, TimestampsMixin


# -------------------------
# 1. Vehicle Model
# -------------------------
class Vehicle(AbstractSQLModel, SoftDeleteMixin, TimestampsMixin):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_number = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_verified = Column(Boolean, default=False)

    owner = relationship("User", back_populates="vehicles")
    reports = relationship("VehicleReport", back_populates="vehicle")
