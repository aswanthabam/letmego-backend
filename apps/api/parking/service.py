from sqlalchemy import select, func, and_, or_, update
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
from sqlalchemy.orm import joinedload, selectinload
from typing import Annotated, Optional, List, Dict, Tuple
from uuid import UUID
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import math
import re

from apps.api.parking.models import (
    ParkingSlot,
    ParkingSlotStaff,
    ParkingSession,
    VehicleDue,
    ParkingVehicleType,
    PricingModel,
    SlotStatus,
    StaffRole,
    SessionStatus,
    PaymentStatus,
    DueStatus
)
from apps.api.parking.schema import (
    ParkingSlotCreate,
    ParkingSlotUpdate,
    StaffAdd,
    StaffAddByEmail,
    SessionCheckIn,
    SessionCheckOut,
    DueCollect,
    SlotVerification,
    SlotAvailability,
    TransactionHistoryItem,
    VehicleTransactionHistory,
    SlotBasicInfo,
)
from avcfastapi.core.database.sqlalchamey.core import SessionDep
from avcfastapi.core.exception.authentication import ForbiddenException
from avcfastapi.core.exception.request import InvalidRequestException
from avcfastapi.core.fastapi.dependency.service_dependency import AbstractService
from apps.api.parking.role_manager import ParkingRoleManager


class ParkingService(AbstractService):
    DEPENDENCIES = {"session": SessionDep}

    def __init__(self, session: SessionDep, **kwargs):
        super().__init__(session=session, **kwargs)
        self.session = session
        self.role_manager = ParkingRoleManager(session)

    # ===== Helper Methods =====

    async def _verify_slot_owner(self, slot_id: UUID, user_id: UUID) -> ParkingSlot:
        """Verify user has administrative access to the slot (Org Admin/Area Manager or Legacy Owner)"""
        slot = await self.session.get(ParkingSlot, slot_id)
        if not slot or slot.deleted_at is not None:
            raise InvalidRequestException("Parking slot not found", error_code="SLOT_NOT_FOUND")
        
        if slot.organization_id:
            from apps.api.organization.models import OrganizationMember, OrganizationRole
            member = await self.session.scalar(
                select(OrganizationMember).where(
                    OrganizationMember.organization_id == slot.organization_id,
                    OrganizationMember.user_id == user_id,
                    OrganizationMember.role.in_([OrganizationRole.ORG_ADMIN, OrganizationRole.AREA_MANAGER]),
                    OrganizationMember.deleted_at.is_(None)
                )
            )
            if not member:
                raise ForbiddenException("You must be an Organization Admin or Area Manager to manage this slot.")
        else:
            # Fallback to legacy check
            if slot.owner_id != user_id:
                raise ForbiddenException("You are not the owner of this parking slot.")
        
        return slot

    async def _verify_slot_staff(self, slot_id: UUID, user_id: UUID):
        """Verify user is staff of the slot (via Organization or Legacy)"""
        slot = await self.session.get(ParkingSlot, slot_id)
        if not slot or slot.deleted_at is not None:
            raise InvalidRequestException("Parking slot not found", error_code="SLOT_NOT_FOUND")
        
        if slot.organization_id:
            from apps.api.organization.models import OrganizationMember
            member = await self.session.scalar(
                select(OrganizationMember).where(
                    OrganizationMember.organization_id == slot.organization_id,
                    OrganizationMember.user_id == user_id,
                    OrganizationMember.deleted_at.is_(None)
                )
            )
            if not member:
                raise ForbiddenException("You do not have staff access to this organization's slots.")
            return slot, member
        else:
            # Fallback to legacy staff check
            staff_record = await self.session.scalar(
                select(ParkingSlotStaff).where(
                    ParkingSlotStaff.slot_id == slot_id,
                    ParkingSlotStaff.user_id == user_id
                )
            )
            
            if not staff_record and slot.owner_id != user_id:
                raise ForbiddenException("You are not authorized to manage this parking slot.")
            
            return slot, staff_record

    def _calculate_parking_fee(
        self,
        slot: ParkingSlot,
        vehicle_type: ParkingVehicleType,
        check_in_time: datetime,
        check_out_time: datetime
    ) -> Decimal:
        """Calculate parking fee based on slot's pricing model"""
        
        if slot.pricing_model == PricingModel.FREE:
            return Decimal("0.00")
        
        # Handle both string and enum types
        vehicle_type_str = vehicle_type.value if isinstance(vehicle_type, ParkingVehicleType) else vehicle_type
        config = slot.pricing_config or {}
        
        if slot.pricing_model == PricingModel.FIXED:
            # Fixed fee per vehicle type
            fee = config.get(vehicle_type_str, 0)
            return Decimal(str(fee))
        
        if slot.pricing_model == PricingModel.HOURLY:
            # Hourly rate: base + incremental
            vehicle_config = config.get(vehicle_type_str, {})
            if not vehicle_config:
                return Decimal("0.00")
            
            base_fee = Decimal(str(vehicle_config.get('base', 0)))
            base_hours = Decimal(str(vehicle_config.get('base_hours', 1)))
            incremental_fee = Decimal(str(vehicle_config.get('incremental', 0)))
            
            # Calculate duration in hours
            duration = check_out_time - check_in_time
            hours = Decimal(str(duration.total_seconds() / 3600))
            
            if hours <= base_hours:
                return base_fee
            
            # Additional hours (ceiling)
            additional_hours = hours - base_hours
            additional_hours_rounded = Decimal(str(math.ceil(float(additional_hours))))
            
            total_fee = base_fee + (additional_hours_rounded * incremental_fee)
            return total_fee.quantize(Decimal("0.01"))
        
        return Decimal("0.00")

    async def _check_vehicle_dues(
        self,
        vehicle_number: str,
        owner_id: UUID
    ) -> Optional[VehicleDue]:
        """Check if vehicle has outstanding dues with this owner"""
        due = await self.session.scalar(
            select(VehicleDue).where(
                VehicleDue.vehicle_number == vehicle_number,
                VehicleDue.slot_owner_id == owner_id,
                VehicleDue.status == DueStatus.PENDING
            )
        )
        return due

    async def _get_live_occupancy(self, slot_id: UUID) -> Dict[str, int]:
        """Calculate current occupancy by vehicle type from counter cache"""
        result = await self.session.execute(
            select(ParkingSlot.current_occupancy)
            .where(ParkingSlot.id == slot_id)
        )
        occupancy = result.scalar_one_or_none()
        return occupancy or {"car": 0, "bike": 0, "truck": 0}

    # ===== NEW: User Management Helper =====
    
    async def _get_user_by_email(self, email: str):
        """Get user by email address"""
        from apps.api.user.models import User  # Import User model
        
        stmt = select(User).where(
            User.email == email,
            User.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _get_vehicle_owner_id(self, vehicle_number: str) -> Optional[UUID]:
        """Get vehicle owner ID from vehicles table if registered"""
        try:
            from apps.api.vehicle.models import Vehicle
            
            stmt = select(Vehicle.user_id).where(
                Vehicle.vehicle_number == vehicle_number,
                Vehicle.deleted_at.is_(None)
            )
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except ImportError:
            # Vehicle module not installed/available
            return None

    # ===== Parking Slot Management =====

    async def create_slot(
        self,
        user_id: UUID,
        slot_data: ParkingSlotCreate
    ) -> ParkingSlot:
        """Create a new parking slot (pending verification)"""
        
        # ISSUE 1 FIX: Validate pricing configuration based on pricing model
        if slot_data.pricing_model == PricingModel.HOURLY:
            if not slot_data.pricing_config:
                raise InvalidRequestException(
                    "Missing pricing configuration for HOURLY model",
                    error_code="MISSING_PRICING_CONFIG"
                )
            
            # Validate HOURLY config has all required vehicle types from capacity
            for vehicle_type in slot_data.capacity.keys():
                if vehicle_type not in slot_data.pricing_config:
                    raise InvalidRequestException(
                        f"Missing pricing configuration for vehicle type: {vehicle_type}",
                        error_code="INCOMPLETE_PRICING_CONFIG"
                    )
                
                config = slot_data.pricing_config[vehicle_type]
                if not isinstance(config, dict):
                    raise InvalidRequestException(
                        f"Invalid pricing configuration for {vehicle_type}",
                        error_code="INVALID_PRICING_CONFIG"
                    )
                
                required_fields = {'base', 'base_hours', 'incremental'}
                if not required_fields.issubset(config.keys()):
                    raise InvalidRequestException(
                        f"Missing required fields in HOURLY config for {vehicle_type}: {required_fields}",
                        error_code="INCOMPLETE_HOURLY_CONFIG"
                    )
        
        elif slot_data.pricing_model == PricingModel.FIXED:
            if not slot_data.pricing_config:
                raise InvalidRequestException(
                    "Missing pricing configuration for FIXED model",
                    error_code="MISSING_PRICING_CONFIG"
                )
            
            # Validate FIXED config has all required vehicle types
            for vehicle_type in slot_data.capacity.keys():
                if vehicle_type not in slot_data.pricing_config:
                    raise InvalidRequestException(
                        f"Missing price for vehicle type: {vehicle_type}",
                        error_code="INCOMPLETE_PRICING_CONFIG"
                    )
        
        elif slot_data.pricing_model == PricingModel.FREE:
            # FREE doesn't need config
            slot_data.pricing_config = {}
        
        # Create slot
        slot = ParkingSlot(
            owner_id=user_id,
            name=slot_data.name,
            description=slot_data.description,
            location=slot_data.location,
            latitude=slot_data.latitude,
            longitude=slot_data.longitude,
            capacity=slot_data.capacity,
            pricing_model=slot_data.pricing_model,
            pricing_config=slot_data.pricing_config or {},
            payment_timing=slot_data.payment_timing,
            status=SlotStatus.PENDING_VERIFICATION,
            organization_id=getattr(slot_data, 'organization_id', None)
        )
        
        # Populate PostGIS geography column from lat/lng for spatial queries
        if slot_data.latitude and slot_data.longitude:
            from sqlalchemy import text
            slot.location_geom = sa.func.ST_GeogFromText(
                f'SRID=4326;POINT({slot_data.longitude} {slot_data.latitude})'
            )
        
        self.session.add(slot)
        await self.session.flush()
        
        # Automatically add owner as staff
        owner_staff = ParkingSlotStaff(
            slot_id=slot.id,
            user_id=user_id,
            role=StaffRole.OWNER
        )
        self.session.add(owner_staff)
        
        await self.session.commit()
        await self.session.refresh(slot)
        
        return slot

    async def get_slot(self, slot_id: UUID) -> ParkingSlot:
        """Get parking slot details"""
        slot = await self.session.get(ParkingSlot, slot_id)
        if not slot or slot.deleted_at is not None:
            raise InvalidRequestException("Parking slot not found", error_code="SLOT_NOT_FOUND")
        return slot

    async def list_my_slots(
        self,
        user_id: UUID,
        status: Optional[SlotStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[ParkingSlot], int]:
        """List parking slots owned by user"""
        query = select(ParkingSlot).where(
            ParkingSlot.owner_id == user_id,
            ParkingSlot.deleted_at.is_(None)
        )
        
        if status:
            query = query.where(ParkingSlot.status == status)
        
        # Get total count
        count_result = await self.session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()
        
        # Get paginated results
        query = query.offset(offset).limit(limit).order_by(ParkingSlot.created_at.desc())
        result = await self.session.execute(query)
        slots = result.scalars().all()
        
        return list(slots), total

    # ISSUE 4 FIX: New method for staff to list their assigned slots
    async def list_staff_slots(
        self,
        user_id: UUID,
        status: Optional[SlotStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[ParkingSlot], int]:
        """List parking slots where user is staff (including owned slots)"""
        
        # Query for slots where user is staff (includes owner role)
        query = (
            select(ParkingSlot)
            .join(ParkingSlotStaff, ParkingSlot.id == ParkingSlotStaff.slot_id)
            .where(
                ParkingSlotStaff.user_id == user_id,
                ParkingSlot.deleted_at.is_(None)
            )
        )
        
        if status:
            query = query.where(ParkingSlot.status == status)
        
        # Get total count
        count_result = await self.session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()
        
        # Get paginated results
        query = query.offset(offset).limit(limit).order_by(ParkingSlot.created_at.desc())
        result = await self.session.execute(query)
        slots = result.unique().scalars().all()
        
        return list(slots), total

    async def update_slot(
        self,
        slot_id: UUID,
        user_id: UUID,
        slot_data: ParkingSlotUpdate
    ) -> ParkingSlot:
        """Update parking slot (owner only, not when active)"""
        slot = await self._verify_slot_owner(slot_id, user_id)
        
        # Can't update active slots (prevents abuse after verification)
        if slot.status == SlotStatus.ACTIVE:
            raise InvalidRequestException(
                "Cannot update active parking slot. Deactivate first.",
                error_code="SLOT_ACTIVE"
            )
        
        # Update fields
        update_data = slot_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(slot, field, value)
        
        await self.session.commit()
        await self.session.refresh(slot)
        
        return slot

    async def delete_slot(self, slot_id: UUID, user_id: UUID) -> bool:
        """Soft delete parking slot (owner only)"""
        slot = await self._verify_slot_owner(slot_id, user_id)
        
        # Can't delete if there are active sessions
        active_sessions = await self.session.scalar(
            select(func.count()).select_from(
                select(ParkingSession).where(
                    ParkingSession.slot_id == slot_id,
                    ParkingSession.status == SessionStatus.CHECKED_IN
                ).subquery()
            )
        )
        
        if active_sessions > 0:
            raise InvalidRequestException(
                "Cannot delete slot with active parking sessions",
                error_code="ACTIVE_SESSIONS_EXIST"
            )
        
        slot.soft_delete()
        await self.session.commit()
        
        return True

    async def get_slot_availability(self, slot_id: UUID) -> SlotAvailability:
        """Get real-time availability for a parking slot"""
        slot = await self.get_slot(slot_id)
        
        # Get current occupancy
        occupied = await self._get_live_occupancy(slot_id)
        
        # Calculate available
        capacity = slot.capacity or {}
        available = {}
        total_capacity = 0
        total_occupied = 0
        
        for vehicle_type, max_count in capacity.items():
            current = occupied.get(vehicle_type, 0)
            available[vehicle_type] = max_count - current
            total_capacity += max_count
            total_occupied += current
        
        occupancy_pct = (total_occupied / total_capacity * 100) if total_capacity > 0 else 0
        
        return SlotAvailability(
            slot_id=slot.id,
            capacity=capacity,
            occupied=occupied,
            available=available,
            occupancy_percentage=round(occupancy_pct, 2)
        )

    # ===== Staff Management =====

    async def add_staff(
        self,
        slot_id: UUID,
        owner_id: UUID,
        staff_data: StaffAdd
    ) -> ParkingSlotStaff:
        """Add staff member to parking slot (owner only)"""
        role = await self.role_manager.verify_owner_access(
            user_id=owner_id,
            slot_id=slot_id
        )
        slot = await self.session.get(ParkingSlot, slot_id)
        #slot = await self._verify_slot_owner(slot_id, owner_id)
                # ISSUE 2 FIX: Only allow adding staff to active slots
        if slot.status != SlotStatus.ACTIVE:
            raise InvalidRequestException(
                "Can only add staff to active parking slots",
                error_code="SLOT_NOT_ACTIVE"
            )
        # Can't add owner as staff again
        if staff_data.user_id == owner_id:
            raise InvalidRequestException("Owner is already staff", error_code="OWNER_AS_STAFF")
        
        # Check if already staff
        existing = await self.session.scalar(
            select(ParkingSlotStaff).where(
                ParkingSlotStaff.slot_id == slot_id,
                ParkingSlotStaff.user_id == staff_data.user_id
            )
        )
        
        if existing:
            raise InvalidRequestException("User is already staff for this slot", error_code="ALREADY_STAFF")
        
        staff = ParkingSlotStaff(
            slot_id=slot_id,
            user_id=staff_data.user_id,
            role=staff_data.role
        )
        
        self.session.add(staff)
        await self.session.commit()
        await self.session.refresh(staff)
        
        return staff

    # ===== NEW: Enhanced Staff Management with Email =====
    
    async def add_staff_by_email(
        self,
        slot_id: UUID,
        owner_id: UUID,
        staff_data: StaffAddByEmail
    ) -> ParkingSlotStaff:
        """
        Add staff member to parking slot by email (owner only).
        Validates that user exists in system before adding.
        """
        slot = await self._verify_slot_owner(slot_id, owner_id)
        # ISSUE 2 FIX: Only allow adding staff to active slots
        if slot.status != SlotStatus.ACTIVE:
            raise InvalidRequestException(
                "Can only add staff to active parking slots",
                error_code="SLOT_NOT_ACTIVE"
            )
        # Check if user exists with this email
        user = await self._get_user_by_email(staff_data.email)
        
        if not user:
            raise InvalidRequestException(
                f"No user found with email: {staff_data.email}. "
                "Please ask them to register first.",
                error_code="USER_NOT_FOUND"
            )
        
        # Can't add owner as staff again
        if user.id == owner_id:
            raise InvalidRequestException(
                "Owner is already staff",
                error_code="OWNER_AS_STAFF"
            )
        
        # Check if already staff
        existing = await self.session.scalar(
            select(ParkingSlotStaff).where(
                ParkingSlotStaff.slot_id == slot_id,
                ParkingSlotStaff.user_id == user.id
            )
        )
        
        if existing:
            raise InvalidRequestException(
                "User is already staff for this slot",
                error_code="ALREADY_STAFF"
            )
        
        staff = ParkingSlotStaff(
            slot_id=slot_id,
            user_id=user.id,
            role=staff_data.role
        )
        
        self.session.add(staff)
        await self.session.commit()
        await self.session.refresh(staff)
        
        return staff

    async def remove_staff(
        self,
        slot_id: UUID,
        staff_user_id: UUID,
        owner_id: UUID
    ) -> bool:
        """Remove staff member from parking slot (owner only)"""
        slot = await self._verify_slot_owner(slot_id, owner_id)
        
        # Can't remove owner
        if staff_user_id == owner_id:
            raise InvalidRequestException("Cannot remove owner from staff", error_code="REMOVE_OWNER")
        
        staff = await self.session.scalar(
            select(ParkingSlotStaff).where(
                ParkingSlotStaff.slot_id == slot_id,
                ParkingSlotStaff.user_id == staff_user_id
            )
        )
        
        if not staff:
            raise InvalidRequestException("Staff member not found", error_code="STAFF_NOT_FOUND")
        
        await self.session.delete(staff)
        await self.session.commit()
        
        return True

    # ISSUE 3 FIX: Enhanced list_staff with user details
    async def list_staff(
        self,
        slot_id: UUID,
        user_id: UUID
    ) -> List[dict]:
        """List staff for parking slot with user details (staff can view)"""
        await self._verify_slot_staff(slot_id, user_id)
        
        from apps.api.user.models import User
        
        # Updated query to join with User table for email
        result = await self.session.execute(
            select(
                ParkingSlotStaff,
                User.email,
                User.name
            )
            .join(User, ParkingSlotStaff.user_id == User.id)
            .where(ParkingSlotStaff.slot_id == slot_id)
        )
        
        # Build response with user details
        staff_list = []
        for staff, email, name in result:
            staff_list.append({
                'id': staff.id,
                'slot_id': staff.slot_id,
                'user_id': staff.user_id,
                'role': staff.role,
                'email': email,  # NEW
                'name': name,    # NEW
                'created_at': staff.created_at
            })
        
        return staff_list
    # ===== Session Management =====

    # ISSUE 6 FIX: Enhanced check-in with due blocking
    async def check_in_vehicle(
        self,
        slot_id: UUID,
        staff_id: UUID,
        check_in_data: SessionCheckIn
    ) -> Tuple[ParkingSession, Optional[VehicleDue]]:
        """
        ENHANCED: Check in a vehicle with automatic owner linking and due blocking.
        """
        slot, staff_record = await self._verify_slot_staff(slot_id, staff_id)
        
        # Verify slot is active
        if slot.status != SlotStatus.ACTIVE:
            raise InvalidRequestException("Parking slot is not active", error_code="SLOT_NOT_ACTIVE")
        
        # Block operations if slot's organization is suspended
        if slot.organization_id:
            from apps.api.organization.models import Organization, OrganizationStatus
            org = await self.session.get(Organization, slot.organization_id)
            if org and org.status == OrganizationStatus.SUSPENDED:
                raise InvalidRequestException(
                    "Organization is suspended. Parking operations are disabled.",
                    error_code="ORG_SUSPENDED"
                )
        
        # Normalize vehicle number for consistent lookups
        normalized_vehicle_number = re.sub(r"[^a-zA-Z0-9]", "", check_in_data.vehicle_number).upper()
        
        # Check if vehicle is already checked in anywhere
        existing_checkin = await self.session.execute(
            select(ParkingSession)
            .where(
                ParkingSession.vehicle_number == normalized_vehicle_number,
                ParkingSession.status == SessionStatus.CHECKED_IN
            )
        )
        existing_session = existing_checkin.scalar_one_or_none()
        
        if existing_session:
            existing_slot = await self.session.get(ParkingSlot, existing_session.slot_id)
            raise InvalidRequestException(
                f"Vehicle {check_in_data.vehicle_number} is already checked in at {existing_slot.name}. "
                f"Please check out from there first or mark as escaped.",
                error_code="ALREADY_CHECKED_IN"
            )
        
        # Check capacity
        availability = await self.get_slot_availability(slot_id)
        vehicle_type_str = check_in_data.vehicle_type.value
        
        if availability.available.get(vehicle_type_str, 0) <= 0:
            raise InvalidRequestException(
                f"No capacity available for {vehicle_type_str}",
                error_code="CAPACITY_FULL"
            )
            
        # Atomic increment of counter cache using raw SQL to prevent race conditions
        await self.session.execute(
            sa.text(
                "UPDATE parking_slots SET current_occupancy = jsonb_set("
                "COALESCE(current_occupancy, '{\"car\": 0, \"bike\": 0, \"truck\": 0}'::jsonb), "
                "ARRAY[:vtype], "
                "(COALESCE((current_occupancy->>:vtype)::int, 0) + 1)::text::jsonb"
                ") WHERE id = :slot_id"
            ),
            {"vtype": vehicle_type_str, "slot_id": str(slot_id)}
        )
        
        # Block checkin if outstanding dues exist with same owner
        outstanding_due = await self._check_vehicle_dues(
            normalized_vehicle_number,
            slot.owner_id
        )
        
        if outstanding_due:
            # Block the checkin - vehicle must pay dues first
            raise InvalidRequestException(
                f"Vehicle {check_in_data.vehicle_number} has outstanding dues of "
                f"₹{outstanding_due.due_amount - outstanding_due.paid_amount:.2f}. "
                f"Please pay the dues before checking in. Due ID: {outstanding_due.id}",
                error_code="OUTSTANDING_DUES_BLOCK"
            )
        
        # Get vehicle owner ID if registered
        vehicle_owner_id = await self._get_vehicle_owner_id(normalized_vehicle_number)
        
        # Create session with normalized vehicle number
        session = ParkingSession(
            slot_id=slot_id,
            vehicle_number=normalized_vehicle_number,
            vehicle_type=check_in_data.vehicle_type.value,
            vehicle_owner_id=vehicle_owner_id,
            checked_in_by=staff_id,
            check_in_time=datetime.now(timezone.utc),
            status=SessionStatus.CHECKED_IN,
            payment_status=PaymentStatus.PENDING,
            calculated_fee=Decimal("0.00"),
            notes=check_in_data.notes
        )
        
        self.session.add(session)
        await self.session.commit()
        await self.session.refresh(session)
        
        # Return session and None for due (since no due if checkin was allowed)
        return session, None

    async def get_active_session_by_vehicle(
        self,
        slot_id: UUID,
        vehicle_number: str
    ) -> Optional[ParkingSession]:
        """Get active session for a vehicle in a specific slot"""
        vehicle_number = re.sub(r"[^a-zA-Z0-9]", "", vehicle_number).upper()
        
        session = await self.session.scalar(
            select(ParkingSession)
            .where(
                ParkingSession.slot_id == slot_id,
                ParkingSession.vehicle_number == vehicle_number,
                ParkingSession.status == SessionStatus.CHECKED_IN
            )
        )
        return session

    async def calculate_fee(
        self,
        session_id: Optional[UUID] = None,
        vehicle_number: Optional[str] = None,
        slot_id: Optional[UUID] = None,
        staff_id: UUID = None
    ) -> dict:
        """Calculate parking fee - accepts either session_id or vehicle_number"""
        
        # Get the session object
        if vehicle_number and slot_id:
            # Support for vehicle number
            session_obj = await self.get_active_session_by_vehicle(slot_id, vehicle_number)
            if not session_obj:
                raise InvalidRequestException(
                    f"No active session found for vehicle {vehicle_number}",
                    error_code="SESSION_NOT_FOUND"
                )
        elif session_id:
            # Traditional way with session_id
            session_obj = await self.session.get(ParkingSession, session_id)
            if not session_obj:
                raise InvalidRequestException("Session not found", error_code="SESSION_NOT_FOUND")
        else:
            raise InvalidRequestException(
                "Provide either session_id or (vehicle_number and slot_id)",
                error_code="INVALID_PARAMS"
            )
        
        # Verify staff access
        await self._verify_slot_staff(session_obj.slot_id, staff_id)
        
        if session_obj.status != SessionStatus.CHECKED_IN:
            raise InvalidRequestException("Session is not checked in", error_code="NOT_CHECKED_IN")
        
        # Get slot for pricing
        slot = await self.session.get(ParkingSlot, session_obj.slot_id)
        
        # Calculate fee
        from datetime import datetime, timezone
        current_time = datetime.now(timezone.utc)
        calculated_fee = self._calculate_parking_fee(
            slot,
            session_obj.vehicle_type,
            session_obj.check_in_time,
            current_time
        )
        
        return {
            'session_id': session_obj.id,
            'vehicle_number': session_obj.vehicle_number,
            'vehicle_type': session_obj.vehicle_type,
            'check_in_time': session_obj.check_in_time,
            'current_time': current_time,
            'duration_hours': (current_time - session_obj.check_in_time).total_seconds() / 3600,
            'calculated_fee': float(calculated_fee),
            'pricing_details': {
                'model': slot.pricing_model,
                'config': slot.pricing_config.get(session_obj.vehicle_type, {}) if slot.pricing_config else {}
            }
        }

    # 3. REPLACE the calculate_checkout_fee method (around line 770-773) with this:
    async def calculate_checkout_fee(self, session_id: UUID, staff_id: UUID) -> dict:
        """Legacy method for backward compatibility - delegates to calculate_fee."""
        return await self.calculate_fee(session_id=session_id, staff_id=staff_id)
    async def check_out_vehicle(
        self,
        staff_id: UUID,
        check_out_data: SessionCheckOut,
        session_id: Optional[UUID] = None,
        vehicle_number: Optional[str] = None,
        slot_id: Optional[UUID] = None
    ) -> ParkingSession:
        """Check out a vehicle - accepts either session_id or vehicle_number"""
        
        if not session_id and not (vehicle_number and slot_id):
            raise InvalidRequestException(
                "Provide either session_id or (vehicle_number and slot_id)",
                error_code="INVALID_PARAMS"
            )
        
        if vehicle_number and slot_id:
            session_obj = await self.get_active_session_by_vehicle(slot_id, vehicle_number)
            if not session_obj:
                raise InvalidRequestException(
                    f"No active session found for vehicle {vehicle_number}",
                    error_code="SESSION_NOT_FOUND"
                )
        else:
            session_obj = await self.session.get(ParkingSession, session_id)
            if not session_obj:
                raise InvalidRequestException("Session not found", error_code="SESSION_NOT_FOUND")
        
        # Verify staff access
        await self._verify_slot_staff(session_obj.slot_id, staff_id)
        
        if session_obj.status != SessionStatus.CHECKED_IN:
            raise InvalidRequestException("Session is not checked in", error_code="NOT_CHECKED_IN")
        
        slot = await self.session.get(ParkingSlot, session_obj.slot_id)
        check_out_time = datetime.now(timezone.utc)
        
        calculated_fee = self._calculate_parking_fee(
            slot,
            session_obj.vehicle_type,
            session_obj.check_in_time,
            check_out_time
        )
        
        # Atomic decrement of counter cache using raw SQL (prevents race conditions)
        vehicle_type_str = session_obj.vehicle_type
        await self.session.execute(
            sa.text(
                "UPDATE parking_slots SET current_occupancy = jsonb_set("
                "COALESCE(current_occupancy, '{\"car\": 0, \"bike\": 0, \"truck\": 0}'::jsonb), "
                "ARRAY[:vtype], "
                "GREATEST(COALESCE((current_occupancy->>:vtype)::int, 0) - 1, 0)::text::jsonb"
                ") WHERE id = :slot_id"
            ),
            {"vtype": vehicle_type_str, "slot_id": str(session_obj.slot_id)}
        )
        
        # Update session
        session_obj.check_out_time = check_out_time
        session_obj.checked_out_by = staff_id
        session_obj.calculated_fee = calculated_fee
        session_obj.collected_fee = check_out_data.collected_fee
        session_obj.payment_mode = check_out_data.payment_mode
        session_obj.status = SessionStatus.CHECKED_OUT
        
        # Payment status logic
        if check_out_data.collected_fee >= calculated_fee:
            session_obj.payment_status = PaymentStatus.PAID
        elif check_out_data.collected_fee > 0:
            session_obj.payment_status = PaymentStatus.PARTIAL
        else:
            session_obj.payment_status = PaymentStatus.PENDING
        
        if check_out_data.notes:
            session_obj.notes = (session_obj.notes or "") + f"\nCheckout: {check_out_data.notes}"
        
        await self.session.commit()
        await self.session.refresh(session_obj)
        
        return session_obj
    # ISSUE 5 FIX: Mark escaped supporting vehicle number
    async def mark_escaped(
        self,
        staff_id: UUID,
        session_id: Optional[UUID] = None,
        vehicle_number: Optional[str] = None,
        slot_id: Optional[UUID] = None
    ) -> Tuple[ParkingSession, VehicleDue]:
        """Mark vehicle as escaped - accepts either session_id or vehicle_number"""
        
        if not session_id and not (vehicle_number and slot_id):
            raise InvalidRequestException(
                "Provide either session_id or (vehicle_number and slot_id)",
                error_code="INVALID_PARAMS"
            )
        
        if vehicle_number and slot_id:
            session_obj = await self.get_active_session_by_vehicle(slot_id, vehicle_number)
            if not session_obj:
                raise InvalidRequestException(
                    f"No active session found for vehicle {vehicle_number}",
                    error_code="SESSION_NOT_FOUND"
                )
        else:
            session_obj = await self.session.get(ParkingSession, session_id)
            if not session_obj:
                raise InvalidRequestException("Session not found", error_code="SESSION_NOT_FOUND")
        
        # Verify staff access
        slot, _ = await self._verify_slot_staff(session_obj.slot_id, staff_id)
        
        if session_obj.status != SessionStatus.CHECKED_IN:
            raise InvalidRequestException("Session is not checked in", error_code="NOT_CHECKED_IN")
        
        # Calculate fee
        escape_time = datetime.now(timezone.utc)
        calculated_fee = self._calculate_parking_fee(
            slot,
            session_obj.vehicle_type,
            session_obj.check_in_time,
            escape_time
        )
        
        # Atomic decrement of counter cache using raw SQL (prevents race conditions)
        vehicle_type_str = session_obj.vehicle_type
        await self.session.execute(
            sa.text(
                "UPDATE parking_slots SET current_occupancy = jsonb_set("
                "COALESCE(current_occupancy, '{\"car\": 0, \"bike\": 0, \"truck\": 0}'::jsonb), "
                "ARRAY[:vtype], "
                "GREATEST(COALESCE((current_occupancy->>:vtype)::int, 0) - 1, 0)::text::jsonb"
                ") WHERE id = :slot_id"
            ),
            {"vtype": vehicle_type_str, "slot_id": str(session_obj.slot_id)}
        )
        
        # Update session
        session_obj.check_out_time = escape_time
        session_obj.checked_out_by = staff_id
        session_obj.calculated_fee = calculated_fee
        session_obj.status = SessionStatus.ESCAPED
        session_obj.payment_status = PaymentStatus.PENDING
        
        # Create due record
        due = VehicleDue(
            vehicle_number=session_obj.vehicle_number,
            slot_owner_id=slot.owner_id,
            session_id=session_obj.id,
            due_amount=calculated_fee,
            paid_amount=Decimal("0.00"),
            status=DueStatus.PENDING
        )
        
        self.session.add(due)
        await self.session.commit()
        await self.session.refresh(session_obj)
        await self.session.refresh(due)
        
        return session_obj, due

    async def list_sessions(
        self,
        slot_id: UUID,
        user_id: UUID,
        status: Optional[SessionStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[ParkingSession], int]:
        """List parking sessions for a slot"""
        await self._verify_slot_staff(slot_id, user_id)
        
        query = select(ParkingSession).where(ParkingSession.slot_id == slot_id)
        
        if status:
            query = query.where(ParkingSession.status == status)
        
        # Get total count
        count_result = await self.session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()
        
        # Get paginated results
        query = query.offset(offset).limit(limit).order_by(ParkingSession.check_in_time.desc())
        result = await self.session.execute(query)
        sessions = result.scalars().all()
        
        return list(sessions), total

    # ===== NEW: Vehicle Transaction History =====
    
    async def get_vehicle_transaction_history(
        self,
        vehicle_number: str,
        requesting_user_id: Optional[UUID] = None,
        limit: int = 100,
        offset: int = 0
    ) -> VehicleTransactionHistory:
        """
        Get complete transaction history for a vehicle number.
        
        Args:
            vehicle_number: Vehicle registration number to search
            requesting_user_id: User requesting the history (optional, for ownership check)
            limit: Maximum records to return
            offset: Pagination offset
        
        Returns:
            Complete transaction history with all sessions and dues
        """
        # Normalize vehicle number
        vehicle_number = re.sub(r"[^a-zA-Z0-9]", "", vehicle_number).upper()
        
        # Check if vehicle is registered
        vehicle_owner_id = await self._get_vehicle_owner_id(vehicle_number)
        is_registered = vehicle_owner_id is not None
        is_owned_by_user = (requesting_user_id == vehicle_owner_id) if vehicle_owner_id else False
        
        # Get all sessions for this vehicle
        sessions_query = (
            select(ParkingSession)
            .where(ParkingSession.vehicle_number == vehicle_number)
            .options(
                joinedload(ParkingSession.slot),
                joinedload(ParkingSession.due)
            )
            .order_by(ParkingSession.check_in_time.desc())
            .offset(offset)
            .limit(limit)
        )
        
        result = await self.session.execute(sessions_query)
        sessions = result.unique().scalars().all()
        
        # Count total sessions
        count_result = await self.session.execute(
            select(func.count()).select_from(
                select(ParkingSession.id)
                .where(ParkingSession.vehicle_number == vehicle_number)
                .subquery()
            )
        )
        total_sessions = count_result.scalar_one()
        
        # Calculate total spent (completed sessions only)
        spent_result = await self.session.execute(
            select(func.sum(ParkingSession.collected_fee))
            .where(
                ParkingSession.vehicle_number == vehicle_number,
                ParkingSession.status == SessionStatus.CHECKED_OUT,
                ParkingSession.collected_fee.isnot(None)
            )
        )
        total_spent = spent_result.scalar_one() or Decimal("0.00")
        
        # Count active sessions
        active_count = await self.session.scalar(
            select(func.count()).select_from(
                select(ParkingSession.id)
                .where(
                    ParkingSession.vehicle_number == vehicle_number,
                    ParkingSession.status == SessionStatus.CHECKED_IN
                )
                .subquery()
            )
        )
        
        # Calculate outstanding dues
        dues_result = await self.session.execute(
            select(func.sum(VehicleDue.due_amount - VehicleDue.paid_amount))
            .where(
                VehicleDue.vehicle_number == vehicle_number,
                VehicleDue.status == DueStatus.PENDING
            )
        )
        outstanding_dues = dues_result.scalar_one() or Decimal("0.00")
        
        # Build transaction list
        transactions = []
        for session in sessions:
            slot_info = SlotBasicInfo(
                id=session.slot.id,
                name=session.slot.name,
                location=session.slot.location,
                pricing_model=session.slot.pricing_model
            )
            
            transaction = TransactionHistoryItem(
                id=session.id,
                slot=slot_info,
                vehicle_number=session.vehicle_number,
                vehicle_type=session.vehicle_type,
                check_in_time=session.check_in_time,
                check_out_time=session.check_out_time,
                status=session.status,
                calculated_fee=session.calculated_fee,
                collected_fee=session.collected_fee,
                payment_mode=session.payment_mode,
                payment_status=session.payment_status,
                is_owned_by_user=is_owned_by_user
            )
            transactions.append(transaction)
        
        return VehicleTransactionHistory(
            vehicle_number=vehicle_number,
            is_registered=is_registered,
            total_sessions=total_sessions,
            total_spent=total_spent,
            active_sessions=active_count,
            outstanding_dues=outstanding_dues,
            transactions=transactions
        )
    
    async def get_my_vehicles_history(
        self,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> Dict:
        """
        Get parking transaction history for all vehicles owned by the user.
        
        Returns:
            Summary of all vehicles and their parking history
        """
        try:
            from apps.api.vehicle.models import Vehicle
            
            # Get all vehicles owned by user
            vehicles_query = (
                select(Vehicle)
                .where(
                    Vehicle.user_id == user_id,
                    Vehicle.deleted_at.is_(None)
                )
            )
            
            result = await self.session.execute(vehicles_query)
            vehicles = result.scalars().all()
            
            if not vehicles:
                return {
                    "total_vehicles": 0,
                    "total_sessions": 0,
                    "total_spent": Decimal("0.00"),
                    "outstanding_dues": Decimal("0.00"),
                    "vehicles": []
                }
            
            # Get transaction history for each vehicle
            vehicle_summaries = []
            total_sessions = 0
            total_spent = Decimal("0.00")
            total_dues = Decimal("0.00")
            
            for vehicle in vehicles:
                # Get session stats for this vehicle
                sessions_count = await self.session.scalar(
                    select(func.count()).select_from(
                        select(ParkingSession.id)
                        .where(ParkingSession.vehicle_number == vehicle.vehicle_number)
                        .subquery()
                    )
                )
                
                # Get total spent
                spent = await self.session.scalar(
                    select(func.sum(ParkingSession.collected_fee))
                    .where(
                        ParkingSession.vehicle_number == vehicle.vehicle_number,
                        ParkingSession.status == SessionStatus.CHECKED_OUT,
                        ParkingSession.collected_fee.isnot(None)
                    )
                ) or Decimal("0.00")
                
                # Get active sessions count
                active = await self.session.scalar(
                    select(func.count()).select_from(
                        select(ParkingSession.id)
                        .where(
                            ParkingSession.vehicle_number == vehicle.vehicle_number,
                            ParkingSession.status == SessionStatus.CHECKED_IN
                        )
                        .subquery()
                    )
                )
                
                # Get outstanding dues
                dues = await self.session.scalar(
                    select(func.sum(VehicleDue.due_amount - VehicleDue.paid_amount))
                    .where(
                        VehicleDue.vehicle_number == vehicle.vehicle_number,
                        VehicleDue.status == DueStatus.PENDING
                    )
                ) or Decimal("0.00")
                
                vehicle_summaries.append({
                    "vehicle_id": vehicle.id,
                    "vehicle_number": vehicle.vehicle_number,
                    "vehicle_name": vehicle.name,
                    "vehicle_type": vehicle.vehicle_type,
                    "total_sessions": sessions_count,
                    "total_spent": float(spent),
                    "active_sessions": active,
                    "outstanding_dues": float(dues)
                })
                
                total_sessions += sessions_count
                total_spent += spent
                total_dues += dues
            
            return {
                "total_vehicles": len(vehicles),
                "total_sessions": total_sessions,
                "total_spent": float(total_spent),
                "outstanding_dues": float(total_dues),
                "vehicles": vehicle_summaries
            }
            
        except ImportError:
            # Vehicle module not installed/available
            return {
                "total_vehicles": 0,
                "total_sessions": 0,
                "total_spent": 0.0,
                "outstanding_dues": 0.0,
                "vehicles": [],
                "error": "Vehicle module not available"
            }

    # ===== Due Management =====

    async def collect_due_payment(
        self,
        due_id: UUID,
        staff_id: UUID,
        payment_data: DueCollect
    ) -> VehicleDue:
        """Collect payment for a vehicle due"""
        due = await self.session.get(VehicleDue, due_id)
        if not due:
            raise InvalidRequestException("Due record not found", error_code="DUE_NOT_FOUND")
        
        if due.status != DueStatus.PENDING:
            raise InvalidRequestException("Due is not pending payment", error_code="NOT_PENDING")
        
        # Verify staff belongs to slot owner
        # Get any slot owned by the due owner
        slot = await self.session.scalar(
            select(ParkingSlot).where(
                ParkingSlot.owner_id == due.slot_owner_id,
                ParkingSlot.deleted_at.is_(None)
            ).limit(1)
        )
        
        if slot:
            await self._verify_slot_staff(slot.id, staff_id)
        else:
            raise ForbiddenException("You are not authorized to collect this payment")
        
        # Update due
        due.paid_amount += payment_data.paid_amount
        due.paid_by_staff = staff_id
        due.paid_at = datetime.now(timezone.utc)
        due.payment_mode = payment_data.payment_mode
        due.payment_session_id = payment_data.payment_session_id
        
        if payment_data.notes:
            due.notes = (due.notes or "") + f"\n{payment_data.notes}"
        
        # Check if fully paid
        if due.paid_amount >= due.due_amount:
            due.status = DueStatus.PAID
        
        await self.session.commit()
        await self.session.refresh(due)
        
        return due

    async def list_dues(
        self,
        owner_id: UUID,
        status: Optional[DueStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[VehicleDue], int]:
        """List vehicle dues for an owner"""
        query = select(VehicleDue).where(VehicleDue.slot_owner_id == owner_id)
        
        if status:
            query = query.where(VehicleDue.status == status)
        
        # Get total count
        count_result = await self.session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()
        
        # Get paginated results
        query = query.offset(offset).limit(limit).order_by(VehicleDue.created_at.desc())
        result = await self.session.execute(query)
        dues = result.scalars().all()
        
        return list(dues), total

    # ===== Admin Functions =====

    async def list_pending_slots(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[ParkingSlot], int]:
        """List slots pending verification (admin only)"""
        query = select(ParkingSlot).where(
            ParkingSlot.status == SlotStatus.PENDING_VERIFICATION,
            ParkingSlot.deleted_at.is_(None)
        )
        
        # Get total count
        count_result = await self.session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()
        
        # Get paginated results
        query = query.offset(offset).limit(limit).order_by(ParkingSlot.created_at.asc())
        result = await self.session.execute(query)
        slots = result.scalars().all()
        
        return list(slots), total

    async def verify_slot(
        self,
        slot_id: UUID,
        admin_id: UUID,
        verification: SlotVerification
    ) -> ParkingSlot:
        """Verify or reject a parking slot (admin only)"""
        slot = await self.get_slot(slot_id)
        
        if slot.status != SlotStatus.PENDING_VERIFICATION:
            raise InvalidRequestException(
                "Slot is not pending verification",
                error_code="NOT_PENDING"
            )
        
        slot.status = verification.status
        slot.verified_by = admin_id
        slot.verified_at = datetime.now(timezone.utc)
        
        if verification.status == SlotStatus.REJECTED:
            slot.rejection_reason = verification.rejection_reason
        
        await self.session.commit()
        await self.session.refresh(slot)
        
        return slot

    async def get_admin_analytics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """Get master analytics for admin"""
        if not start_date:
            start_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        if not end_date:
            end_date = datetime.now(timezone.utc)
        
        # Total slots
        total_slots = await self.session.scalar(
            select(func.count()).select_from(
                select(ParkingSlot).where(ParkingSlot.deleted_at.is_(None)).subquery()
            )
        )
        
        # Active slots
        active_slots = await self.session.scalar(
            select(func.count()).select_from(
                select(ParkingSlot).where(
                    ParkingSlot.status == SlotStatus.ACTIVE,
                    ParkingSlot.deleted_at.is_(None)
                ).subquery()
            )
        )
        
        # Total revenue
        total_revenue = await self.session.scalar(
            select(func.sum(ParkingSession.collected_fee)).where(
                ParkingSession.check_out_time >= start_date,
                ParkingSession.check_out_time <= end_date,
                ParkingSession.status.in_([SessionStatus.CHECKED_OUT])
            )
        ) or Decimal("0.00")
        
        # Total sessions
        total_sessions = await self.session.scalar(
            select(func.count()).select_from(
                select(ParkingSession).where(
                    ParkingSession.check_in_time >= start_date,
                    ParkingSession.check_in_time <= end_date
                ).subquery()
            )
        )
        
        # Outstanding dues
        outstanding_dues = await self.session.scalar(
            select(func.sum(VehicleDue.due_amount - VehicleDue.paid_amount)).where(
                VehicleDue.status == DueStatus.PENDING
            )
        ) or Decimal("0.00")
        
        return {
            "date_range": {
                "start_date": start_date,
                "end_date": end_date
            },
            "total_slots": total_slots,
            "active_slots": active_slots,
            "total_revenue": float(total_revenue),
            "total_sessions": total_sessions,
            "total_outstanding_dues": float(outstanding_dues)
        }

    # ===== Public Endpoints =====

    async def find_nearby_parking_slots(
            self,
            latitude: float,
            longitude: float,
            radius_km: float = 5.0,
            limit: int = 20
        ) -> List[Dict]:
            """
            Find active parking slots near a location with real-time availability.
            Public endpoint - no authentication required.
            
            Uses PostGIS GiST spatial indexing for ultra-fast radius searches.
            """
            
            # PostGIS works in meters for Geography columns
            radius_meters = radius_km * 1000
            
            # Create a WKT string for the search point
            search_point = f'SRID=4326;POINT({longitude} {latitude})'
            
            # Query active slots within radius using PostGIS ST_DWithin
            # Calculate exact distance using ST_Distance
            query = select(
                ParkingSlot,
                func.ST_Distance(
                    ParkingSlot.location_geom,
                    func.ST_GeogFromText(search_point)
                ).label('distance_meters')
            ).where(
                ParkingSlot.status == SlotStatus.ACTIVE,
                ParkingSlot.deleted_at.is_(None),
                func.ST_DWithin(
                    ParkingSlot.location_geom,
                    func.ST_GeogFromText(search_point),
                    radius_meters
                )
            ).order_by(
                'distance_meters'
            ).limit(limit)
            
            result = await self.session.execute(query)
            slots_with_distance = result.all()
            
            # Build response using counter cache (no N+1 queries)
            nearby_slots = []
            for slot, distance_meters in slots_with_distance:
                capacity = slot.capacity or {}
                occupied = dict(slot.current_occupancy) if slot.current_occupancy else {"car": 0, "bike": 0, "truck": 0}
                available = {}
                total_capacity = 0
                total_occupied = 0
                for vt, max_count in capacity.items():
                    current = occupied.get(vt, 0)
                    available[vt] = max(max_count - current, 0)
                    total_capacity += max_count
                    total_occupied += current
                occupancy_pct = round((total_occupied / total_capacity * 100), 2) if total_capacity > 0 else 0
                
                nearby_slots.append({
                    "id": slot.id,
                    "name": slot.name,
                    "description": slot.description,
                    "location": slot.location,
                    "latitude": slot.latitude,
                    "longitude": slot.longitude,
                    "distance_km": round(float(distance_meters) / 1000, 2),
                    "capacity": capacity,
                    "pricing_model": slot.pricing_model,
                    "pricing_config": slot.pricing_config,
                    "payment_timing": slot.payment_timing,
                    "availability": available,
                    "occupancy_percentage": occupancy_pct
                })
            
            return nearby_slots


ParkingServiceDependency = Annotated[ParkingService, ParkingService.get_dependency()]