from sqlalchemy import Column, String, Boolean, UUID
from sqlalchemy.orm import relationship
import sqlalchemy as sa

from core.db.base import AbstractSQLModel
from core.db.mixins import SoftDeleteMixin, TimestampsMixin
from core.storage.fields import S3ImageField


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
    profile_picture = Column(
        S3ImageField(
            upload_to="user/profile_picture/",
            variations={
                "thumbnail": {"width": 150, "height": 150},
                "medium": {"width": 500, "height": 500},
                "large": {"width": 800, "height": 800},
            },
        ),
        nullable=True,
    )

    vehicles = relationship("Vehicle", back_populates="owner")
    reports = relationship("VehicleReport", back_populates="reporter")
