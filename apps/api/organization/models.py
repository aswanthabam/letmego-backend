import enum
import sqlalchemy as sa
from sqlalchemy import Column, String, Enum as SQLEnum, ForeignKey, UUID, UniqueConstraint
from sqlalchemy.orm import relationship

from avcfastapi.core.database.sqlalchamey.base import AbstractSQLModel
from avcfastapi.core.database.sqlalchamey.mixins import SoftDeleteMixin, TimestampsMixin


class OrganizationType(str, enum.Enum):
    PARKING_OPERATOR = "parking_operator"
    PROPERTY_MANAGER = "property_manager"
    HYBRID = "hybrid"


class OrganizationStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"


class OrganizationRole(str, enum.Enum):
    ORG_ADMIN = "org_admin"      # Full financial and operational control
    AREA_MANAGER = "area_manager" # Can manage slots/apartments but no billing
    GROUND_STAFF = "ground_staff" # Can only check-in/out and view permitted vehicles


class Organization(AbstractSQLModel, SoftDeleteMixin, TimestampsMixin):
    __tablename__ = "organizations"

    name = Column(String(200), nullable=False)
    type = Column(SQLEnum(OrganizationType), nullable=False, default=OrganizationType.PARKING_OPERATOR)
    status = Column(SQLEnum(OrganizationStatus), nullable=False, default=OrganizationStatus.ACTIVE)
    billing_plan = Column(String(100), nullable=True)
    
    # Relationships
    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")


class OrganizationMember(AbstractSQLModel, SoftDeleteMixin, TimestampsMixin):
    __tablename__ = "organization_members"
    
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(SQLEnum(OrganizationRole), nullable=False, default=OrganizationRole.GROUND_STAFF)
    
    # Relationships
    organization = relationship("Organization", back_populates="members")

    __table_args__ = (
        UniqueConstraint('organization_id', 'user_id', name='uq_org_member'),
    )
