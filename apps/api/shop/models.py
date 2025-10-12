# apps/api/shop/models.py

from sqlalchemy import Column, String, Float, Text, UUID
import sqlalchemy as sa

from avcfastapi.core.database.sqlalchamey.base import AbstractSQLModel
from avcfastapi.core.database.sqlalchamey.mixins import SoftDeleteMixin, TimestampsMixin


class Shop(AbstractSQLModel, SoftDeleteMixin, TimestampsMixin):
    """
    Shop Model for storing shop information including location
    """
    __tablename__ = "shops"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        default=sa.text("gen_random_uuid()"),
    )
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    address = Column(String(500), nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    phone_number = Column(String(20), nullable=True)
    email = Column(String(120), nullable=True)
    website = Column(String(200), nullable=True)
    category = Column(String(100), nullable=True)  # e.g., Restaurant, Retail, Service, etc.
    operating_hours = Column(String(200), nullable=True)  # e.g., "Mon-Fri: 9AM-6PM"
    is_active = Column(sa.Boolean, default=True, nullable=False)
