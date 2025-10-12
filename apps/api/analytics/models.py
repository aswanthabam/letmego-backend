# apps/api/analytics/models.py

from sqlalchemy import Column, String, UUID, ForeignKey, DateTime, JSON
import sqlalchemy as sa
from datetime import datetime

from avcfastapi.core.database.sqlalchamey.base import AbstractSQLModel
from avcfastapi.core.database.sqlalchamey.mixins import TimestampsMixin


class CallToActionEvent(AbstractSQLModel, TimestampsMixin):
    """
    Model to track call-to-action button clicks and events
    """
    __tablename__ = "cta_events"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        default=sa.text("gen_random_uuid()"),
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True  # Allow anonymous tracking
    )
    event_type = Column(
        String(100),
        nullable=False,
        index=True  # For faster queries
    )  # e.g., "contact_shop", "view_vehicle", "report_issue", etc.
    event_context = Column(
        String(200),
        nullable=True
    )  # Additional context like "from_shop_page", "from_vehicle_detail"
    related_entity_id = Column(
        UUID(as_uuid=True),
        nullable=True
    )  # ID of related entity (shop_id, vehicle_id, etc.)
    related_entity_type = Column(
        String(50),
        nullable=True
    )  # Type of entity ("shop", "vehicle", "user", etc.)
    metadata = Column(
        JSON,
        nullable=True
    )  # Additional metadata as JSON
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)
