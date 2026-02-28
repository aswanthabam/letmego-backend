# apps/api/organization/schema.py

from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from typing import Optional, List
from datetime import datetime

from apps.api.organization.models import OrganizationType, OrganizationStatus, OrganizationRole


class OrganizationBase(BaseModel):
    name: str = Field(..., max_length=200)
    type: OrganizationType = Field(default=OrganizationType.PARKING_OPERATOR)
    billing_plan: Optional[str] = Field(None, max_length=100)


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    type: Optional[OrganizationType] = None
    status: Optional[OrganizationStatus] = None
    billing_plan: Optional[str] = Field(None, max_length=100)


class OrganizationResponse(OrganizationBase):
    id: UUID
    status: OrganizationStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrganizationMemberBase(BaseModel):
    role: OrganizationRole = Field(default=OrganizationRole.GROUND_STAFF)


class OrganizationMemberAdd(OrganizationMemberBase):
    user_id: str  # Either ID or Email
    is_email: bool = False


class OrganizationMemberUpdate(OrganizationMemberBase):
    pass


class OrganizationMemberResponse(OrganizationMemberBase):
    id: UUID
    organization_id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
