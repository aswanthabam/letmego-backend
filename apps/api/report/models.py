from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text
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


# -------------------------
# 1. Vehicle Report Model
# -------------------------
class VehicleReport(AbstractSQLModel, SoftDeleteMixin, TimestampsMixin):
    __tablename__ = "vehicle_reports"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    notes = Column(Text, nullable=True)

    vehicle = relationship("Vehicle", back_populates="reports")
    reporter = relationship("User", back_populates="reports")
    images = relationship(
        "VehicleReportImage", back_populates="report", cascade="all, delete-orphan"
    )


# -------------------------
# 2. Report Image Model
# -------------------------
class VehicleReportImage(AbstractSQLModel, SoftDeleteMixin, TimestampsMixin):
    __tablename__ = "vehicle_report_images"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("vehicle_reports.id"), nullable=False)
    image_url = Column(String(255), nullable=False)

    report = relationship("VehicleReport", back_populates="images")
