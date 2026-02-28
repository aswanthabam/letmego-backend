"""
Organization Service encapsulating logic for B2B SaaS Multi-Tenancy
"""
from typing import Annotated, List, Tuple
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from avcfastapi.core.database.sqlalchamey.core import SessionDep
from avcfastapi.core.fastapi.dependency.service_dependency import AbstractService
from avcfastapi.core.exception.request import InvalidRequestException
from avcfastapi.core.exception.authentication import ForbiddenException

from apps.api.organization.models import Organization, OrganizationMember, OrganizationRole
from apps.api.organization.schema import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationMemberAdd,
    OrganizationMemberUpdate
)
from apps.api.user.models import User


class OrganizationService(AbstractService):
    DEPENDENCIES = {"session": SessionDep}

    def __init__(self, session: SessionDep, **kwargs):
        super().__init__(session=session, **kwargs)
        self.session = session

    async def get_organization(self, org_id: UUID) -> Organization:
        """Fetch organization by ID"""
        org = await self.session.get(Organization, org_id)
        if not org or org.deleted_at is not None:
            raise InvalidRequestException("Organization not found", error_code="ORG_NOT_FOUND")
        return org

    async def create_organization(self, user_id: UUID, data: OrganizationCreate) -> Organization:
        """Creates a new Organization and sets the creator as the ORG_ADMIN"""
        
        org = Organization(
            name=data.name,
            type=data.type,
            billing_plan=data.billing_plan
        )
        self.session.add(org)
        await self.session.flush() # flush to generate UUID

        # Create founder member
        member = OrganizationMember(
            organization_id=org.id,
            user_id=user_id,
            role=OrganizationRole.ORG_ADMIN
        )
        self.session.add(member)
        
        await self.session.commit()
        await self.session.refresh(org)
        
        return org

    async def update_organization(self, org_id: UUID, user_id: UUID, data: OrganizationUpdate) -> Organization:
        """Updates an Organization (Requires ORG_ADMIN)"""
        await self._verify_org_admin(org_id, user_id)
        
        org = await self.get_organization(org_id)
        
        if data.name:
            org.name = data.name
        if data.type:
            org.type = data.type
        if data.status:
            org.status = data.status
        if data.billing_plan is not None:
            org.billing_plan = data.billing_plan
            
        await self.session.commit()
        await self.session.refresh(org)
        return org

    async def _verify_org_admin(self, org_id: UUID, user_id: UUID) -> OrganizationMember:
        """Helper to ensure user is an ORG_ADMIN for the given organization"""
        member = await self.session.scalar(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == user_id,
                OrganizationMember.role == OrganizationRole.ORG_ADMIN,
                OrganizationMember.deleted_at.is_(None)
            )
        )
        if not member:
            raise ForbiddenException("You must be an Organization Admin to perform this action")
        return member

    async def verify_org_membership(self, org_id: UUID, user_id: UUID, allowed_roles: List[OrganizationRole] = None) -> OrganizationMember:
        """Helper to check if user belongs to an org, optionally verifying roles"""
        member = await self.session.scalar(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == user_id,
                OrganizationMember.deleted_at.is_(None)
            )
        )
        if not member:
            raise ForbiddenException("You do not have access to this Organization")
            
        if allowed_roles and member.role not in allowed_roles:
            raise ForbiddenException(f"Insufficient Organization Role. Required one of: {[r.value for r in allowed_roles]}")
            
        return member


OrganizationServiceDependency = Annotated[OrganizationService, OrganizationService.get_dependency()]
