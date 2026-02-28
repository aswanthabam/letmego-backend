# apps/api/organization/router.py

from fastapi import APIRouter, Depends, Query
from typing import List
from uuid import UUID

from avcfastapi.core.fastapi.dependency.authentication_dependency import AuthenticationDependency
from avcfastapi.core.fastapi.response_models import SuccessResponse, PaginatedResponse

from apps.api.organization.schema import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
)
from apps.api.organization.service import OrganizationServiceDependency


router = APIRouter(prefix="/v1/organizations", tags=["Organizations"])


@router.post("", response_model=SuccessResponse[OrganizationResponse])
async def create_organization(
    data: OrganizationCreate,
    auth: AuthenticationDependency,
    service: OrganizationServiceDependency
):
    """Create a new Multi-Tenant Organization"""
    org = await service.create_organization(auth.user.id, data)
    return SuccessResponse(data=org, message="Organization created successfully")


@router.patch("/{org_id}", response_model=SuccessResponse[OrganizationResponse])
async def update_organization(
    org_id: UUID,
    data: OrganizationUpdate,
    auth: AuthenticationDependency,
    service: OrganizationServiceDependency
):
    """Edit Organization details. Target user must be ORG_ADMIN."""
    org = await service.update_organization(org_id, auth.user.id, data)
    return SuccessResponse(data=org, message="Organization updated successfully")
