from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from core.db.base import AbstractSQLModel
from core.db.mixins import SoftDeleteMixin, TimestampsMixin


# -------------------------
# 1. User Model
# -------------------------
class User(AbstractSQLModel, SoftDeleteMixin, TimestampsMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String(128), unique=True, nullable=False)  # Firebase UID
    firstname = Column(String(50), nullable=False)
    lastname = Column(String(50), nullable=False)
    email = Column(String(120), unique=True, nullable=False)

    vehicles = relationship("Vehicle", back_populates="owner")
    reports = relationship("VehicleReport", back_populates="reporter")
