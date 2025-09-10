from sqlalchemy import Column, Enum, String, Boolean, UUID
from sqlalchemy.orm import relationship
import sqlalchemy as sa
from enum import Enum as PyEnum

from apps.storage import default_storage
from avcfastapi.core.database.sqlalchamey.base import AbstractSQLModel
from avcfastapi.core.database.sqlalchamey.mixins import SoftDeleteMixin, TimestampsMixin
from avcfastapi.core.storage.sqlalchemy.fields.imagefield import ImageField


class PrivacyPreference(PyEnum):
    PUBLIC = "public"
    PRIVATE = "private"
    ANONYMOUS = "anonymous"


class UserRoles(PyEnum):
    USER = "user"
    ADMIN = "admin"


class UserStatus(PyEnum):
    REGISTERED = "registered"
    PROFILE_COMPLETED = "profile_completed"
    VEHICLE_ADDED = "vehicle_added"


# -------------------------
# 1. User Model
# -------------------------
class User(AbstractSQLModel, SoftDeleteMixin, TimestampsMixin):
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        default=sa.text("gen_random_uuid()"),
    )
    uid = Column(String(128), unique=True, nullable=False)  # Firebase UID
    fullname = Column(String(120), nullable=False)
    email = Column(String(120), nullable=True)
    email_verified = Column(Boolean, default=False)
    phone_number = Column(String(120), nullable=True)
    role = Column(
        String(20),
        default=UserRoles.USER.value,
        nullable=False,
        server_default=UserRoles.USER.value,
    )
    profile_picture = Column(
        ImageField(
            storage=default_storage,
            upload_to="user/profile_picture/",
            variations={
                "thumbnail": {"width": 150, "height": 150},
                "medium": {"width": 500, "height": 500},
                "large": {"width": 800, "height": 800},
            },
        ),
        nullable=True,
    )
    company_name = Column(String(100), nullable=True)
    privacy_preference = Column(
        String(20),
        default=PrivacyPreference.PUBLIC.value,
        nullable=False,
        server_default=PrivacyPreference.PUBLIC.value,
    )
    status = Column(
        String(20),
        default=UserStatus.REGISTERED.value,
        nullable=False,
        server_default=UserStatus.REGISTERED.value,
    )

    vehicles = relationship("Vehicle", back_populates="owner")
    reports = relationship("VehicleReport", back_populates="reporter")
    devices = relationship("Device", back_populates="user")
