import uuid
from sqlalchemy import UUID, Column, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timezone

from apps.api.notification.schema import (
    ChannelDeliveryStatus,
    NotificationCategory,
    NotificationStatus,
)
from core.db.base import AbstractSQLModel
from core.db.fields import TZAwareDateTime
from core.db.mixins import SoftDeleteMixin, TimestampsMixin
from apps.storage import default_storage
from core.storage.sqlalchemy.fields.imagefield import ImageField


class Notification(AbstractSQLModel, SoftDeleteMixin, TimestampsMixin):
    """
    Represents a conceptual notification, independent of delivery channel.
    """

    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    title = Column(String(255), nullable=True)
    body = Column(String, nullable=True)
    data = Column(
        JSONB, nullable=True, comment="Generic data payload for the notification"
    )
    image = Column(
        ImageField(
            storage=default_storage,
            upload_to="notifications/images/",
            variations={
                "thumbnail": {"width": 150, "height": 150},
                "medium": {"width": 500, "height": 500},
                "large": {"width": 800, "height": 800},
            },
        )
    )
    notification_type = Column(
        String(20),
        default=NotificationCategory.IN_APP.value,
        nullable=False,
        index=True,
    )
    redirection_target = Column(
        String(500), nullable=True, comment="URL or identifier for redirection on click"
    )
    status = Column(
        String(20),
        default=NotificationStatus.UNREAD.value,
        nullable=False,
        index=True,
    )

    user = relationship("User")
    channels = relationship("NotificationChannel", back_populates="notification")


class NotificationChannel(AbstractSQLModel, SoftDeleteMixin, TimestampsMixin):
    """
    Logs the details of a notification sent via a specific channel (e.g., FCM, In-App).
    """

    __tablename__ = "notification_channels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notification_id = Column(
        UUID(as_uuid=True), ForeignKey("notifications.id"), nullable=False, index=True
    )
    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey("devices.id"),
        nullable=True,
        index=True,
        comment="Optional: For device-specific channels like FCM Push",
    )

    channel_type = Column(String(20), nullable=False, index=True)

    channel_specific_data = Column(
        JSONB,
        nullable=True,
        comment="JSON payload for channel-specific details (e.g., FCM message ID, error codes)",
    )

    status = Column(
        String(20),
        default=ChannelDeliveryStatus.PENDING.value,
        nullable=False,
        index=True,
    )

    sent_at = Column(
        TZAwareDateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    delivered_at = Column(TZAwareDateTime(timezone=True), nullable=True)
    seen_at = Column(TZAwareDateTime(timezone=True), nullable=True)

    error_message = Column(String, nullable=True)

    notification = relationship("Notification", back_populates="channels")
