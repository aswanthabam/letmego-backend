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

from apps.api.organization.models import Organization, OrganizationMember, OrganizationRole, OrganizationStatus
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

    async def ensure_org_active(self, org_id: UUID) -> Organization:
        """Verify org exists AND is active (not suspended). Use before any operation."""
        org = await self.get_organization(org_id)
        if org.status == OrganizationStatus.SUSPENDED:
            raise InvalidRequestException(
                "Organization is suspended. Contact support.",
                error_code="ORG_SUSPENDED"
            )
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

    async def add_member(self, org_id: UUID, admin_user_id: UUID, target_user_id: UUID, role: OrganizationRole) -> OrganizationMember:
        """Add a member to an organization. Requires ORG_ADMIN or AREA_MANAGER."""
        await self.ensure_org_active(org_id)
        await self._verify_org_admin(org_id, admin_user_id)
        
        # Check target user exists
        target_user = await self.session.get(User, target_user_id)
        if not target_user or target_user.deleted_at is not None:
            raise InvalidRequestException("Target user not found", error_code="USER_NOT_FOUND")
        
        # Check not already a member
        existing = await self.session.scalar(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == target_user_id,
                OrganizationMember.deleted_at.is_(None)
            )
        )
        if existing:
            raise InvalidRequestException("User is already a member of this organization", error_code="ALREADY_MEMBER")
        
        member = OrganizationMember(
            organization_id=org_id,
            user_id=target_user_id,
            role=role
        )
        self.session.add(member)
        await self.session.commit()
        await self.session.refresh(member)
        return member

    async def remove_member(self, org_id: UUID, admin_user_id: UUID, target_user_id: UUID) -> bool:
        """Remove a member from an organization. Prevents removing the last ORG_ADMIN."""
        await self.ensure_org_active(org_id)
        await self._verify_org_admin(org_id, admin_user_id)
        
        member = await self.session.scalar(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == target_user_id,
                OrganizationMember.deleted_at.is_(None)
            )
        )
        if not member:
            raise InvalidRequestException("Member not found in this organization", error_code="MEMBER_NOT_FOUND")
        
        # LAST-ADMIN PROTECTION: If removing an admin, ensure at least one other admin remains
        if member.role == OrganizationRole.ORG_ADMIN:
            admin_count = await self.session.scalar(
                select(func.count()).select_from(
                    select(OrganizationMember).where(
                        OrganizationMember.organization_id == org_id,
                        OrganizationMember.role == OrganizationRole.ORG_ADMIN,
                        OrganizationMember.deleted_at.is_(None)
                    ).subquery()
                )
            )
            if admin_count <= 1:
                raise InvalidRequestException(
                    "Cannot remove the last organization admin. "
                    "Promote another member to admin first.",
                    error_code="LAST_ADMIN"
                )
        
        member.soft_delete()
        await self.session.commit()
        return True

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
