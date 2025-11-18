# apps/api/parking/role_manager.py

"""
Role Context Manager for Parking System

Solves the multi-role problem where a single user can be:
- Owner of some parking slots
- Staff/Volunteer in other parking slots  
- Regular user parking their vehicle

This module provides context-aware role management and permission checking.
"""

from typing import Optional, List, Set, Dict
from uuid import UUID
from enum import Enum
from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.parking.models import (
    ParkingSlot,
    ParkingSlotStaff,
    StaffRole,
    SlotStatus
)
from avcfastapi.core.exception.authentication import ForbiddenException
from avcfastapi.core.exception.request import InvalidRequestException


class UserRoleContext(str, Enum):
    """Context in which user is operating"""
    OWNER = "owner"          # Acting as slot owner
    STAFF = "staff"          # Acting as staff/volunteer
    CUSTOMER = "customer"    # Acting as regular parking customer
    ADMIN = "admin"          # Acting as system admin


@dataclass
class UserSlotRole:
    """Represents a user's role in a specific parking slot"""
    slot_id: UUID
    user_id: UUID
    role: StaffRole
    slot_owner_id: UUID
    slot_name: str
    slot_status: SlotStatus
    
    @property
    def is_owner(self) -> bool:
        return self.role == StaffRole.OWNER
    
    @property
    def is_staff(self) -> bool:
        return self.role in [StaffRole.STAFF, StaffRole.VOLUNTEER]
    
    @property
    def can_manage_staff(self) -> bool:
        """Only owners can add/remove staff"""
        return self.is_owner
    
    @property
    def can_check_in_out(self) -> bool:
        """All staff (owner, staff, volunteer) can check in/out vehicles"""
        return True
    
    @property
    def can_collect_dues(self) -> bool:
        """All staff can collect dues"""
        return True
    
    @property
    def can_view_analytics(self) -> bool:
        """Only owners can view detailed analytics"""
        return self.is_owner


@dataclass
class UserRolesSummary:
    """Summary of all roles a user has in the system"""
    user_id: UUID
    owned_slots: List[UUID]
    staff_slots: Dict[UUID, StaffRole]  # slot_id -> role
    total_slots_with_access: int
    
    @property
    def is_slot_owner(self) -> bool:
        return len(self.owned_slots) > 0
    
    @property
    def is_staff_anywhere(self) -> bool:
        return len(self.staff_slots) > 0
    
    def get_role_for_slot(self, slot_id: UUID) -> Optional[StaffRole]:
        """Get user's role for a specific slot"""
        return self.staff_slots.get(slot_id)
    
    def has_access_to_slot(self, slot_id: UUID) -> bool:
        """Check if user has any access to the slot"""
        return slot_id in self.staff_slots


class ParkingRoleManager:
    """
    Manages role context and permissions for parking operations.
    
    This class solves the multi-role problem by:
    1. Tracking what role(s) a user has for each slot
    2. Providing context-aware permission checks
    3. Separating owner, staff, and customer operations
    """
    
    def __init__(self, session: Session):
        self.session = session
    
    # ===== Role Discovery =====
    
    async def get_user_roles_summary(self, user_id: UUID) -> UserRolesSummary:
        """
        Get a complete summary of all roles this user has in the system.
        
        Returns information about:
        - Which slots they own
        - Which slots they're staff at
        - Their specific role in each slot
        """
        stmt = (
            select(ParkingSlotStaff, ParkingSlot)
            .join(ParkingSlot, ParkingSlot.id == ParkingSlotStaff.slot_id)
            .where(
                ParkingSlotStaff.user_id == user_id,
                ParkingSlot.deleted_at.is_(None)
            )
        )
        
        result = await self.session.execute(stmt)
        rows = result.all()
        
        owned_slots = []
        staff_slots = {}
        
        for staff_record, slot in rows:
            staff_slots[slot.id] = staff_record.role
            if staff_record.role == StaffRole.OWNER:
                owned_slots.append(slot.id)
        
        return UserRolesSummary(
            user_id=user_id,
            owned_slots=owned_slots,
            staff_slots=staff_slots,
            total_slots_with_access=len(staff_slots)
        )
    
    async def get_user_role_for_slot(
        self,
        user_id: UUID,
        slot_id: UUID
    ) -> Optional[UserSlotRole]:
        """
        Get user's specific role and permissions for a parking slot.
        Returns None if user has no role in this slot.
        """
        stmt = (
            select(ParkingSlotStaff, ParkingSlot)
            .join(ParkingSlot, ParkingSlot.id == ParkingSlotStaff.slot_id)
            .where(
                ParkingSlotStaff.user_id == user_id,
                ParkingSlotStaff.slot_id == slot_id,
                ParkingSlot.deleted_at.is_(None)
            )
        )
        
        result = await self.session.execute(stmt)
        row = result.first()
        
        if not row:
            return None
        
        staff_record, slot = row
        
        return UserSlotRole(
            slot_id=slot.id,
            user_id=user_id,
            role=staff_record.role,
            slot_owner_id=slot.owner_id,
            slot_name=slot.name,
            slot_status=slot.status
        )
    
    async def get_all_user_slot_roles(
        self,
        user_id: UUID,
        status_filter: Optional[SlotStatus] = None
    ) -> List[UserSlotRole]:
        """
        Get all slots where user has any role, with their specific role in each.
        Useful for displaying "My Workplaces" or "My Slots" views.
        """
        stmt = (
            select(ParkingSlotStaff, ParkingSlot)
            .join(ParkingSlot, ParkingSlot.id == ParkingSlotStaff.slot_id)
            .where(
                ParkingSlotStaff.user_id == user_id,
                ParkingSlot.deleted_at.is_(None)
            )
        )
        
        if status_filter:
            stmt = stmt.where(ParkingSlot.status == status_filter)
        
        result = await self.session.execute(stmt)
        rows = result.all()
        
        roles = []
        for staff_record, slot in rows:
            roles.append(UserSlotRole(
                slot_id=slot.id,
                user_id=user_id,
                role=staff_record.role,
                slot_owner_id=slot.owner_id,
                slot_name=slot.name,
                slot_status=slot.status
            ))
        
        return roles
    
    # ===== Permission Checking =====
    
    async def verify_owner_access(
        self,
        user_id: UUID,
        slot_id: UUID
    ) -> UserSlotRole:
        """
        Verify user is the OWNER of the slot.
        Raises exception if not owner.
        
        Use this for operations that only owners can do:
        - Adding/removing staff
        - Updating slot configuration
        - Viewing detailed analytics
        - Deleting slot
        """
        role = await self.get_user_role_for_slot(user_id, slot_id)
        
        if not role:
            raise ForbiddenException(
                "You don't have access to this parking slot"
            )
        
        if not role.is_owner:
            raise ForbiddenException(
                f"You are a {role.role.value} at '{role.slot_name}', "
                "but only the owner can perform this operation"
            )
        
        return role
    
    async def verify_staff_access(
        self,
        user_id: UUID,
        slot_id: UUID,
        require_active: bool = True
    ) -> UserSlotRole:
        """
        Verify user has staff access (owner, staff, or volunteer).
        Raises exception if not staff.
        
        Use this for operations that any staff can do:
        - Check in/out vehicles
        - View slot availability
        - Collect dues
        - View basic stats
        
        Args:
            require_active: If True, slot must be ACTIVE status
        """
        role = await self.get_user_role_for_slot(user_id, slot_id)
        
        if not role:
            raise ForbiddenException(
                "You don't have access to this parking slot"
            )
        
        if require_active and role.slot_status != SlotStatus.ACTIVE:
            raise InvalidRequestException(
                f"Cannot perform operations on slot with status: {role.slot_status.value}. "
                "Slot must be ACTIVE.",
                error_code="SLOT_NOT_ACTIVE"
            )
        
        return role
    
    async def check_slot_capacity_for_staff(
        self,
        user_id: UUID,
        slot_id: UUID
    ) -> bool:
        """
        Check if user can perform staff operations on this slot.
        Returns True if they can, False otherwise.
        Does not raise exceptions.
        """
        role = await self.get_user_role_for_slot(user_id, slot_id)
        return role is not None
    
    # ===== Slot Queries with Role Context =====
    
    async def get_slots_where_user_is_owner(
        self,
        user_id: UUID,
        status_filter: Optional[SlotStatus] = None
    ) -> List[ParkingSlot]:
        """Get all slots where user is the owner"""
        stmt = (
            select(ParkingSlot)
            .join(ParkingSlotStaff, ParkingSlot.id == ParkingSlotStaff.slot_id)
            .where(
                ParkingSlotStaff.user_id == user_id,
                ParkingSlotStaff.role == StaffRole.OWNER,
                ParkingSlot.deleted_at.is_(None)
            )
        )
        
        if status_filter:
            stmt = stmt.where(ParkingSlot.status == status_filter)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_slots_where_user_is_staff(
        self,
        user_id: UUID,
        status_filter: Optional[SlotStatus] = None,
        exclude_owned: bool = False
    ) -> List[ParkingSlot]:
        """
        Get all slots where user is staff (not owner).
        Useful for "Where do I work?" queries.
        """
        stmt = (
            select(ParkingSlot)
            .join(ParkingSlotStaff, ParkingSlot.id == ParkingSlotStaff.slot_id)
            .where(
                ParkingSlotStaff.user_id == user_id,
                ParkingSlot.deleted_at.is_(None)
            )
        )
        
        if exclude_owned:
            stmt = stmt.where(ParkingSlotStaff.role != StaffRole.OWNER)
        
        if status_filter:
            stmt = stmt.where(ParkingSlot.status == status_filter)
        
        result = await self.session.execute(stmt)
        return list(result.unique().scalars().all())
    
    # ===== Role-based Operation Helpers =====
    
    async def get_owner_slots_for_dues(
        self,
        user_id: UUID
    ) -> List[UUID]:
        """
        Get list of slot owner IDs where user is the owner.
        Used for cross-slot due tracking.
        
        When a vehicle escapes without paying, the due is tracked
        against the owner_id so it applies across all their slots.
        """
        slots = await self.get_slots_where_user_is_owner(user_id)
        return [slot.id for slot in slots]
    
    async def can_user_collect_due(
        self,
        user_id: UUID,
        due_owner_id: UUID
    ) -> bool:
        """
        Check if user can collect a due.
        User can collect if they're staff at any slot owned by due_owner_id.
        """
        # Get all slots owned by the due owner
        owner_slots = await self.get_slots_where_user_is_owner(due_owner_id)
        owner_slot_ids = {slot.id for slot in owner_slots}
        
        # Check if user is staff at any of these slots
        user_roles = await self.get_user_roles_summary(user_id)
        
        for slot_id in owner_slot_ids:
            if user_roles.has_access_to_slot(slot_id):
                return True
        
        return False
    
    # ===== Context-Aware Messages =====
    
    def get_permission_error_message(
        self,
        user_role: Optional[UserSlotRole],
        required_role: UserRoleContext,
        operation: str
    ) -> str:
        """
        Generate helpful error messages that explain the user's current role
        and what role they need for the operation.
        """
        if not user_role:
            return (
                f"You don't have access to this parking slot. "
                f"To {operation}, you need to be {required_role.value}."
            )
        
        return (
            f"You are currently a {user_role.role.value} at '{user_role.slot_name}'. "
            f"To {operation}, you need to be the {required_role.value}. "
            "Please contact the owner if you believe this is incorrect."
        )


# ===== Dependency Injection =====

async def get_role_manager(session) -> ParkingRoleManager:
    """FastAPI dependency for role manager"""
    return ParkingRoleManager(session)


# ===== Usage Examples =====

"""
EXAMPLE 1: Check-in a vehicle (staff operation)

async def check_in_vehicle(
    slot_id: UUID,
    user_id: UUID,
    vehicle_data: SessionCheckIn,
    role_manager: ParkingRoleManager
):
    # Verify user is staff (any staff role can do this)
    role = await role_manager.verify_staff_access(
        user_id=user_id,
        slot_id=slot_id,
        require_active=True
    )
    
    # Now we know:
    # - User has staff access
    # - Slot is active
    # - User's specific role is in role.role
    
    # Proceed with check-in...
    print(f"{role.role.value} at {role.slot_name} is checking in vehicle")


EXAMPLE 2: Add staff member (owner-only operation)

async def add_staff_member(
    slot_id: UUID,
    user_id: UUID,
    new_staff_data: StaffAdd,
    role_manager: ParkingRoleManager
):
    # Verify user is owner (not just staff)
    role = await role_manager.verify_owner_access(
        user_id=user_id,
        slot_id=slot_id
    )
    
    # Now we know user is definitely the owner
    # Proceed with adding staff...


EXAMPLE 3: Show user their workplaces

async def get_my_workplaces(
    user_id: UUID,
    role_manager: ParkingRoleManager
):
    # Get all slots where user has any role
    roles = await role_manager.get_all_user_slot_roles(
        user_id=user_id,
        status_filter=SlotStatus.ACTIVE
    )
    
    # Group by role type
    owned = [r for r in roles if r.is_owner]
    staff = [r for r in roles if r.is_staff]
    
    return {
        "owned_slots": owned,
        "staff_slots": staff,
        "total": len(roles)
    }


EXAMPLE 4: Context-aware error messages

async def some_owner_operation(
    slot_id: UUID,
    user_id: UUID,
    role_manager: ParkingRoleManager
):
    try:
        role = await role_manager.verify_owner_access(user_id, slot_id)
        # ... do owner stuff ...
    except ForbiddenException:
        # Get user's actual role for helpful error
        user_role = await role_manager.get_user_role_for_slot(user_id, slot_id)
        message = role_manager.get_permission_error_message(
            user_role=user_role,
            required_role=UserRoleContext.OWNER,
            operation="add staff members"
        )
        # Returns: "You are currently a staff at 'Downtown Parking'. 
        #           To add staff members, you need to be the owner."
        raise ForbiddenException(message)
"""