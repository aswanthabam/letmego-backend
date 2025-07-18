from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

from apps.api.device.schema import DeviceStatus
from core.db.base import AbstractSQLModel
from core.db.fields import TZAwareDateTime
from core.db.mixins import SoftDeleteMixin, TimestampsMixin


class Device(AbstractSQLModel, SoftDeleteMixin, TimestampsMixin):
    __tablename__ = "devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )

    device_token = Column(String(250), unique=True, nullable=False, index=True)
    device_model = Column(String(50), nullable=True)
    platform = Column(String(15), nullable=False)
    os_version = Column(String(25), nullable=True)
    app_version = Column(String(20), nullable=True)
    language_code = Column(String(10), nullable=True, default="en")

    status = Column(
        String(20),
        default=DeviceStatus.ACTIVE.value,
        server_default=DeviceStatus.ACTIVE.value,
        nullable=False,
        index=True,
    )
    last_seen = Column(
        TZAwareDateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    push_enabled = Column(
        String(20),
        default="UNKNOWN",
        nullable=False,
    )

    user = relationship("User", back_populates="devices")
