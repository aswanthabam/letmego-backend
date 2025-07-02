from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, UUID
from sqlalchemy.orm import relationship
import sqlalchemy as sa

from core.db.base import AbstractSQLModel
from core.db.mixins import SoftDeleteMixin, TimestampsMixin


# -------------------------
# 1. Vehicle Report Model
# -------------------------
class VehicleReport(AbstractSQLModel, SoftDeleteMixin, TimestampsMixin):
    __tablename__ = "vehicle_reports"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        default=sa.text("gen_random_uuid()"),
    )
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
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

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        default=sa.text("gen_random_uuid()"),
    )
    report_id = Column(
        UUID(as_uuid=True), ForeignKey("vehicle_reports.id"), nullable=False
    )
    image_url = Column(String(255), nullable=False)

    report = relationship("VehicleReport", back_populates="images")
