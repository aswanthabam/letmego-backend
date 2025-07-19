from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    ForeignKey,
    Text,
    UUID,
    Sequence,
)
from sqlalchemy.orm import relationship
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from core.db.base import AbstractSQLModel
from core.db.mixins import SoftDeleteMixin, TimestampsMixin
from core.storage.sqlalchemy.fields.imagefield import ImageField
from apps.storage import default_storage


report_number_seq = Sequence("report_number_seq", start=1000)


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
        unique=True,
    )
    report_number = Column(
        Integer,
        report_number_seq,
        server_default=report_number_seq.next_value(),
        unique=True,
        nullable=False,
        primary_key=True,  # Optional: only if it's the PK
    )
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    notes = Column(Text, nullable=True)
    current_status = Column(String(50), nullable=False, default="active")
    is_anonymous = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    is_closed = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    vehicle = relationship("Vehicle", back_populates="reports")
    reporter = relationship("User", back_populates="reports")
    images = relationship(
        "VehicleReportImage", back_populates="report", cascade="all, delete-orphan"
    )
    status_logs = relationship(
        "VehicleReportStatusLog",
        back_populates="report",
    )
    chat_messages = relationship(
        "ChatMessage",
        back_populates="report",
        cascade="all, delete-orphan",
        uselist=True,
    )
    latitude = Column(
        String(20),
        nullable=True,
        doc="Latitude of the report location",
    )
    longitude = Column(
        String(20),
        nullable=True,
        doc="Longitude of the report location",
    )
    location = Column(
        String(255),
        nullable=True,
        doc="Human-readable location of the report",
    )

    @property
    def reporter_name(self):
        if not self.reporter:
            return "Unknown"
        if self.reporter.privacy_preference.value == "anonymous":
            return "Anonymous"
        return self.reporter.fullname


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
    image = Column(
        ImageField(
            storage=default_storage,
            upload_to="vehicle/reports/images/",
            variations={
                "thumbnail": {"width": 150, "height": 150},
                "medium": {"width": 500, "height": 500},
                "large": {"width": 800, "height": 800},
            },
        ),
        nullable=True,
    )

    report = relationship("VehicleReport", back_populates="images")


class VehicleReportStatusLog(AbstractSQLModel, TimestampsMixin):
    __tablename__ = "vehicle_report_status_logs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        default=sa.text("gen_random_uuid()"),
    )
    report_id = Column(
        UUID(as_uuid=True), ForeignKey("vehicle_reports.id"), nullable=False
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    data = Column(JSONB, nullable=True)
    status = Column(String(50), nullable=False)
    notes = Column(String(255), nullable=True)

    report = relationship("VehicleReport", back_populates="status_logs")
