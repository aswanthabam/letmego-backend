# apps/api/parking/service_enhanced.py

"""
Enhanced Parking Service with Role Context Management

This is a refactored version of the parking service that uses the RoleManager
to handle multi-role scenarios properly. Users can operate in different contexts:
- As owner of their slots
- As staff at other people's slots
- As regular customers parking their vehicles

Key improvements:
1. Clear separation of owner vs staff operations
2. Context-aware permission checking
3. Better error messages that explain user's current role
4. Support for users who are both owners and staff
"""

from sqlalchemy import select, func, and_, or_
import sqlalchemy as sa
from sqlalchemy.orm import joinedload, selectinload
from typing import Optional, List, Dict, Tuple
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
)
from apps.api.parking.role_manager import (
    ParkingRoleManager,
    UserRoleContext,
    UserSlotRole
)
from avcfastapi.core.database.sqlalchamey.core import SessionDep
from avcfastapi.core.exception.authentication import ForbiddenException
from avcfastapi.core.exception.request import InvalidRequestException
from avcfastapi.core.fastapi.dependency.service_dependency import AbstractService


class EnhancedParkingService(AbstractService):
    """
    Enhanced parking service with proper role context management.
    
    This service separates operations by role context:
    - Owner operations: create, update, delete slots, add staff, view analytics
    - Staff operations: check in/out vehicles, collect dues, view availability
    - Customer operations: search nearby slots, view own parking history
    """
    
    DEPENDENCIES = {"session": SessionDep}

    def __init__(self, session: SessionDep, **kwargs):
        super().__init__(session=session, **kwargs)
        self.session = session
        self.role_manager = ParkingRoleManager(session)

    # ===== OWNER OPERATIONS =====
    # These operations require owner role
    
    async def create_slot_as_owner(
        self,
        user_id: UUID,
        slot_data: ParkingSlotCreate
    ) -> ParkingSlot:
        """
        Create a new parking slot as owner.
        User will be automatically added as OWNER staff.
        
        Context: OWNER
        """
        # Validate pricing configuration
        self._validate_pricing_config(slot_data)
        
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
            status=SlotStatus.PENDING_VERIFICATION
        )
        
        self.session.add(slot)
        await self.session.flush()
        
        # Automatically add user as owner staff
        owner_staff = ParkingSlotStaff(
            slot_id=slot.id,
            user_id=user_id,
            role=StaffRole.OWNER
        )
        self.session.add(owner_staff)
        
        await self.session.commit()
        await self.session.refresh(slot)
        
        return slot
    
    async def update_slot_as_owner(
        self,
        slot_id: UUID,
        user_id: UUID,
        slot_data: ParkingSlotUpdate
    ) -> ParkingSlot:
        """
        Update parking slot configuration.
        Only owner can do this, and only when slot is not active.
        
        Context: OWNER (verified)
        """
        # Verify owner access
        role = await self.role_manager.verify_owner_access(user_id, slot_id)
        
        # Get the slot
        slot = await self.session.get(ParkingSlot, slot_id)
        
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
    
    async def delete_slot_as_owner(
        self,
        slot_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        Soft delete parking slot.
        Only owner can do this, and only when no active sessions exist.
        
        Context: OWNER (verified)
        """
        # Verify owner access
        role = await self.role_manager.verify_owner_access(user_id, slot_id)
        
        slot = await self.session.get(ParkingSlot, slot_id)
        
        # Can't delete if there are active sessions
        active_sessions = await self.session.scalar(
            select(func.count(ParkingSession.id)).where(
                ParkingSession.slot_id == slot_id,
                ParkingSession.status == SessionStatus.CHECKED_IN
            )
        )
        
        if active_sessions > 0:
            raise InvalidRequestException(
                f"Cannot delete slot with {active_sessions} active parking session(s). "
                "Please check out all vehicles first.",
                error_code="ACTIVE_SESSIONS_EXIST"
            )
        
        slot.soft_delete()
        await self.session.commit()
        
        return True
    
    async def add_staff_as_owner(
        self,
        slot_id: UUID,
        user_id: UUID,
        staff_data: StaffAdd
    ) -> ParkingSlotStaff:
        """
        Add a staff member to the parking slot.
        Only owner can add staff, and only to active slots.
        
        Context: OWNER (verified)
        """
        # Verify owner access
        role = await self.role_manager.verify_owner_access(user_id, slot_id)
        
        slot = await self.session.get(ParkingSlot, slot_id)
        
        # Only allow adding staff to active slots
        if slot.status != SlotStatus.ACTIVE:
            raise InvalidRequestException(
                "Can only add staff to ACTIVE parking slots",
                error_code="SLOT_NOT_ACTIVE"
            )
        
        # Can't add owner as staff again
        if staff_data.user_id == user_id:
            raise InvalidRequestException(
                "You are already the owner of this slot",
                error_code="OWNER_AS_STAFF"
            )
        
        # Check if already staff
        existing = await self.session.scalar(
            select(ParkingSlotStaff).where(
                ParkingSlotStaff.slot_id == slot_id,
                ParkingSlotStaff.user_id == staff_data.user_id
            )
        )
        
        if existing:
            raise InvalidRequestException(
                "This user is already staff for this slot",
                error_code="ALREADY_STAFF"
            )
        
        # Add staff
        staff = ParkingSlotStaff(
            slot_id=slot_id,
            user_id=staff_data.user_id,
            role=staff_data.role
        )
        
        self.session.add(staff)
        await self.session.commit()
        await self.session.refresh(staff)
        
        return staff
    
    async def remove_staff_as_owner(
        self,
        slot_id: UUID,
        staff_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        Remove a staff member from the parking slot.
        Only owner can remove staff.
        
        Context: OWNER (verified)
        """
        # Verify owner access
        role = await self.role_manager.verify_owner_access(user_id, slot_id)
        
        # Get staff record
        staff = await self.session.get(ParkingSlotStaff, staff_id)
        
        if not staff or staff.slot_id != slot_id:
            raise InvalidRequestException("Staff member not found")
        
        # Can't remove owner
        if staff.role == StaffRole.OWNER:
            raise InvalidRequestException(
                "Cannot remove the owner from staff list",
                error_code="CANNOT_REMOVE_OWNER"
            )
        
        await self.session.delete(staff)
        await self.session.commit()
        
        return True
    
    async def list_my_owned_slots(
        self,
        user_id: UUID,
        status: Optional[SlotStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[ParkingSlot], int]:
        """
        List all parking slots owned by the user.
        
        Context: OWNER
        """
        slots = await self.role_manager.get_slots_where_user_is_owner(
            user_id=user_id,
            status_filter=status
        )
        
        # Apply pagination
        total = len(slots)
        paginated_slots = slots[offset:offset + limit]
        
        return paginated_slots, total
    
    # ===== STAFF OPERATIONS =====
    # These operations require staff access (owner, staff, or volunteer)
    
    async def check_in_vehicle_as_staff(
        self,
        slot_id: UUID,
        user_id: UUID,
        vehicle_data: SessionCheckIn
    ) -> ParkingSession:
        """
        Check in a vehicle to the parking slot.
        Any staff member (owner, staff, volunteer) can do this.
        
        Context: STAFF (verified)
        """
        # Verify staff access (slot must be active)
        role = await self.role_manager.verify_staff_access(
            user_id=user_id,
            slot_id=slot_id,
            require_active=True
        )
        
        slot = await self.session.get(ParkingSlot, slot_id)
        
        # Normalize vehicle number
        vehicle_number = self._normalize_vehicle_number(vehicle_data.vehicle_number)
        
        # Check if vehicle is already checked in
        existing = await self.session.scalar(
            select(ParkingSession).where(
                ParkingSession.slot_id == slot_id,
                ParkingSession.vehicle_number == vehicle_number,
                ParkingSession.status == SessionStatus.CHECKED_IN
            )
        )
        
        if existing:
            raise InvalidRequestException(
                f"Vehicle {vehicle_number} is already checked in at this slot",
                error_code="VEHICLE_ALREADY_CHECKED_IN"
            )
        
        # Check capacity
        await self._verify_capacity_available(slot, vehicle_data.vehicle_type)
        
        # Check for outstanding dues
        due = await self._check_vehicle_dues(vehicle_number, slot.owner_id)
        
        # Get vehicle owner if registered
        vehicle_owner_id = await self._get_vehicle_owner_id(vehicle_number)
        
        # Create session
        session = ParkingSession(
            slot_id=slot_id,
            vehicle_number=vehicle_number,
            vehicle_type=vehicle_data.vehicle_type,
            vehicle_owner_id=vehicle_owner_id,
            checked_in_by=user_id,
            check_in_time=datetime.now(timezone.utc),
            status=SessionStatus.CHECKED_IN,
            calculated_fee=Decimal("0.00"),
            payment_status=PaymentStatus.PENDING,
            notes=vehicle_data.notes
        )
        
        self.session.add(session)
        await self.session.commit()
        await self.session.refresh(session)
        
        # Return session with due alert if exists
        if due:
            session.has_outstanding_due = True
            session.due_amount = due.due_amount - due.paid_amount
            session.due_id = due.id
        
        return session
    
    async def check_out_vehicle_as_staff(
        self,
        session_id: UUID,
        user_id: UUID,
        checkout_data: SessionCheckOut
    ) -> ParkingSession:
        """
        Check out a vehicle and collect payment.
        Any staff member can do this.
        
        Context: STAFF (verified)
        """
        # Get session
        session = await self.session.get(ParkingSession, session_id)
        
        if not session:
            raise InvalidRequestException("Parking session not found")
        
        # Verify staff access to this slot
        role = await self.role_manager.verify_staff_access(
            user_id=user_id,
            slot_id=session.slot_id,
            require_active=True
        )
        
        # Verify session is checked in
        if session.status != SessionStatus.CHECKED_IN:
            raise InvalidRequestException(
                f"Cannot check out: session status is {session.status.value}",
                error_code="INVALID_SESSION_STATUS"
            )
        
        # Get slot for fee calculation
        slot = await self.session.get(ParkingSlot, session.slot_id)
        
        # Calculate fee
        check_out_time = datetime.now(timezone.utc)
        calculated_fee = self._calculate_parking_fee(
            slot=slot,
            vehicle_type=session.vehicle_type,
            check_in_time=session.check_in_time,
            check_out_time=check_out_time
        )
        
        # Update session
        session.check_out_time = check_out_time
        session.checked_out_by = user_id
        session.calculated_fee = calculated_fee
        session.collected_fee = checkout_data.collected_fee
        session.payment_mode = checkout_data.payment_mode
        session.notes = checkout_data.notes or session.notes
        
        # Determine payment status
        if checkout_data.collected_fee >= calculated_fee:
            session.payment_status = PaymentStatus.PAID
            session.status = SessionStatus.CHECKED_OUT
        elif checkout_data.collected_fee > 0:
            session.payment_status = PaymentStatus.PARTIAL
            session.status = SessionStatus.CHECKED_OUT
            
            # Create due for remaining amount
            await self._create_vehicle_due(
                session=session,
                slot_owner_id=slot.owner_id,
                due_amount=calculated_fee - checkout_data.collected_fee
            )
        else:
            session.payment_status = PaymentStatus.PENDING
            session.status = SessionStatus.ESCAPED
            
            # Create full due
            await self._create_vehicle_due(
                session=session,
                slot_owner_id=slot.owner_id,
                due_amount=calculated_fee
            )
        
        await self.session.commit()
        await self.session.refresh(session)
        
        return session
    
    async def list_my_staff_slots(
        self,
        user_id: UUID,
        status: Optional[SlotStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[ParkingSlot], int]:
        """
        List all parking slots where user is staff (including owned slots).
        
        Context: STAFF
        """
        slots = await self.role_manager.get_slots_where_user_is_staff(
            user_id=user_id,
            status_filter=status,
            exclude_owned=False  # Include owned slots
        )
        
        # Apply pagination
        total = len(slots)
        paginated_slots = slots[offset:offset + limit]
        
        return paginated_slots, total
    
    async def get_slot_availability_as_staff(
        self,
        slot_id: UUID,
        user_id: UUID
    ) -> SlotAvailability:
        """
        Get real-time availability for a parking slot.
        Any staff member can view this.
        
        Context: STAFF (verified)
        """
        # Verify staff access
        role = await self.role_manager.verify_staff_access(
            user_id=user_id,
            slot_id=slot_id,
            require_active=False  # Can view even if inactive
        )
        
        return await self._calculate_slot_availability(slot_id)
    
    async def collect_due_as_staff(
        self,
        due_id: UUID,
        user_id: UUID,
        payment_data: DueCollect
    ) -> VehicleDue:
        """
        Collect payment for an outstanding vehicle due.
        Any staff member working for the slot owner can collect.
        
        Context: STAFF (verified)
        """
        # Get due
        due = await self.session.get(VehicleDue, due_id)
        
        if not due:
            raise InvalidRequestException("Due not found")
        
        if due.status != DueStatus.PENDING:
            raise InvalidRequestException(
                f"Cannot collect: due status is {due.status.value}",
                error_code="DUE_NOT_PENDING"
            )
        
        # Verify user can collect this due
        can_collect = await self.role_manager.can_user_collect_due(
            user_id=user_id,
            due_owner_id=due.slot_owner_id
        )
        
        if not can_collect:
            raise ForbiddenException(
                "You don't have permission to collect payments for this parking slot owner"
            )
        
        # Update due
        due.paid_amount += payment_data.paid_amount
        
        if due.paid_amount >= due.due_amount:
            due.status = DueStatus.PAID
            due.paid_at = datetime.now(timezone.utc)
        else:
            # Partial payment not allowed by schema validation,
            # but keeping this for completeness
            pass
        
        due.paid_by_staff = user_id
        due.payment_session_id = payment_data.payment_session_id
        due.payment_mode = payment_data.payment_mode
        due.notes = payment_data.notes or due.notes
        
        await self.session.commit()
        await self.session.refresh(due)
        
        return due
    
    # ===== CUSTOMER OPERATIONS =====
    # These operations don't require slot access
    
    async def find_nearby_parking_public(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0,
        limit: int = 20
    ) -> List[Dict]:
        """
        Find active parking slots near a location (public endpoint).
        Anyone can use this.
        
        Context: CUSTOMER (no authentication needed)
        """
        # Use Haversine formula to calculate distance
        # This is a simplified version - for production use PostGIS
        
        stmt = (
            select(ParkingSlot)
            .where(
                ParkingSlot.status == SlotStatus.ACTIVE,
                ParkingSlot.deleted_at.is_(None)
            )
        )
        
        result = await self.session.execute(stmt)
        all_slots = result.scalars().all()
        
        # Calculate distances and filter
        nearby_slots = []
        for slot in all_slots:
            distance = self._calculate_distance(
                latitude, longitude,
                slot.latitude, slot.longitude
            )
            
            if distance <= radius_km:
                # Get availability
                availability = await self._calculate_slot_availability(slot.id)
                
                nearby_slots.append({
                    "id": slot.id,
                    "name": slot.name,
                    "description": slot.description,
                    "location": slot.location,
                    "latitude": slot.latitude,
                    "longitude": slot.longitude,
                    "distance_km": round(distance, 2),
                    "capacity": slot.capacity,
                    "pricing_model": slot.pricing_model,
                    "pricing_config": slot.pricing_config,
                    "payment_timing": slot.payment_timing,
                    "availability": availability.available,
                    "occupancy_percentage": availability.occupancy_percentage
                })
        
        # Sort by distance and limit
        nearby_slots.sort(key=lambda x: x["distance_km"])
        return nearby_slots[:limit]
    
    # ===== HELPER METHODS =====
    
    def _validate_pricing_config(self, slot_data: ParkingSlotCreate):
        """Validate pricing configuration matches pricing model"""
        if slot_data.pricing_model == PricingModel.FREE:
            slot_data.pricing_config = {}
            return
        
        if not slot_data.pricing_config:
            raise InvalidRequestException(
                f"pricing_config required for {slot_data.pricing_model.value} model",
                error_code="MISSING_PRICING_CONFIG"
            )
        
        # Validate all vehicle types in capacity have pricing
        for vehicle_type in slot_data.capacity.keys():
            if vehicle_type not in slot_data.pricing_config:
                raise InvalidRequestException(
                    f"Missing pricing for vehicle type: {vehicle_type}",
                    error_code="INCOMPLETE_PRICING_CONFIG"
                )
    
    def _normalize_vehicle_number(self, vehicle_number: str) -> str:
        """Normalize vehicle number format"""
        return re.sub(r"[^a-zA-Z0-9]", "", vehicle_number).upper()
    
    async def _verify_capacity_available(
        self,
        slot: ParkingSlot,
        vehicle_type: ParkingVehicleType
    ):
        """Check if there's capacity for this vehicle type"""
        capacity = slot.capacity.get(vehicle_type.value, 0)
        
        if capacity <= 0:
            raise InvalidRequestException(
                f"This parking slot does not accept {vehicle_type.value}s",
                error_code="VEHICLE_TYPE_NOT_ACCEPTED"
            )
        
        # Get current occupancy
        current_count = await self.session.scalar(
            select(func.count(ParkingSession.id)).where(
                ParkingSession.slot_id == slot.id,
                ParkingSession.vehicle_type == vehicle_type.value,
                ParkingSession.status == SessionStatus.CHECKED_IN
            )
        )
        
        if current_count >= capacity:
            raise InvalidRequestException(
                f"No space available for {vehicle_type.value}s (capacity: {capacity})",
                error_code="NO_CAPACITY"
            )
    
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
        
        vehicle_type_str = vehicle_type.value if isinstance(vehicle_type, ParkingVehicleType) else vehicle_type
        config = slot.pricing_config or {}
        
        if slot.pricing_model == PricingModel.FIXED:
            fee = config.get(vehicle_type_str, 0)
            return Decimal(str(fee))
        
        if slot.pricing_model == PricingModel.HOURLY:
            vehicle_config = config.get(vehicle_type_str, {})
            if not vehicle_config:
                return Decimal("0.00")
            
            base_fee = Decimal(str(vehicle_config.get('base', 0)))
            base_hours = Decimal(str(vehicle_config.get('base_hours', 1)))
            incremental_fee = Decimal(str(vehicle_config.get('incremental', 0)))
            
            duration = check_out_time - check_in_time
            hours = Decimal(str(duration.total_seconds() / 3600))
            
            if hours <= base_hours:
                return base_fee
            
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
        """Check if vehicle has outstanding dues"""
        due = await self.session.scalar(
            select(VehicleDue).where(
                VehicleDue.vehicle_number == vehicle_number,
                VehicleDue.slot_owner_id == owner_id,
                VehicleDue.status == DueStatus.PENDING
            )
        )
        return due
    
    async def _create_vehicle_due(
        self,
        session: ParkingSession,
        slot_owner_id: UUID,
        due_amount: Decimal
    ):
        """Create a due record for escaped vehicle"""
        due = VehicleDue(
            vehicle_number=session.vehicle_number,
            slot_owner_id=slot_owner_id,
            session_id=session.id,
            due_amount=due_amount,
            paid_amount=Decimal("0.00"),
            status=DueStatus.PENDING
        )
        self.session.add(due)
    
    async def _get_vehicle_owner_id(self, vehicle_number: str) -> Optional[UUID]:
        """Get vehicle owner from vehicles table if exists"""
        try:
            from apps.api.vehicle.models import Vehicle
            
            stmt = select(Vehicle.user_id).where(
                Vehicle.vehicle_number == vehicle_number,
                Vehicle.deleted_at.is_(None)
            )
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except ImportError:
            return None
    
    async def _calculate_slot_availability(
        self,
        slot_id: UUID
    ) -> SlotAvailability:
        """Calculate real-time slot availability"""
        slot = await self.session.get(ParkingSlot, slot_id)
        
        # Get occupancy by vehicle type
        result = await self.session.execute(
            select(
                ParkingSession.vehicle_type,
                func.count(ParkingSession.id)
            )
            .where(
                ParkingSession.slot_id == slot_id,
                ParkingSession.status == SessionStatus.CHECKED_IN
            )
            .group_by(ParkingSession.vehicle_type)
        )
        
        occupied = dict(result.all())
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
    
    def _calculate_distance(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two points using Haversine formula"""
        from math import radians, cos, sin, asin, sqrt
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        
        # Earth radius in kilometers
        r = 6371
        
        return c * r
# At the bottom of service_enhanced.py

from typing import Annotated

EnhancedParkingServiceDependency = Annotated[
    EnhancedParkingService, 
    EnhancedParkingService.get_dependency()
]

