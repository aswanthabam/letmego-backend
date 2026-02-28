# apps/api/parking/router.py

from typing import Optional, List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Query, Request
from apps.api.parking.service_enhanced import EnhancedParkingServiceDependency

from apps.api.auth.dependency import UserDependency, AdminUserDependency
from apps.api.parking.service import ParkingServiceDependency
from apps.api.parking.schema import (
    ParkingSlotCreate,
    ParkingSlotUpdate,
    ParkingSlotResponse,
    SlotAvailability,
    StaffAdd,
    StaffAddByEmail,  # NEW
    StaffResponse,
    SessionCheckIn,
    SessionCheckOut,
    SessionResponse,
    SessionWithDueAlert,
    DueCollect,
    DueResponse,
    SlotVerification,
    OwnerAnalytics,
    AdminAnalytics,
    NearbySlotResponse,
    VehicleTransactionHistory,  # NEW
)
from apps.api.parking.models import SlotStatus, SessionStatus, DueStatus
from avcfastapi.core.fastapi.response.models import MessageResponse
from avcfastapi.core.fastapi.response.pagination import (
    PaginatedResponse,
    PaginationParams,
    paginated_response,
)

router = APIRouter(
    prefix="/parking",
    tags=["Parking Management"],
)


# ===== Public Endpoints (No Authentication Required) =====

@router.get("/public/nearby", description="Find nearby parking slots (Public)")
async def find_nearby_parking(
    parking_service: ParkingServiceDependency,
    latitude: float = Query(..., description="Your current latitude", ge=-90, le=90),
    longitude: float = Query(..., description="Your current longitude", ge=-180, le=180),
    radius_km: float = Query(5.0, description="Search radius in kilometers", ge=0.1, le=50),
    limit: int = Query(20, description="Maximum number of results", ge=1, le=100)
) -> List[NearbySlotResponse]:
    """
    Find active parking slots near your location with real-time availability.
    
    **Public endpoint** - No authentication required.
    
    **Parameters:**
    - latitude: Your current latitude (-90 to 90)
    - longitude: Your current longitude (-180 to 180)
    - radius_km: Search radius in kilometers (default: 5km, max: 50km)
    - limit: Maximum results to return (default: 20, max: 100)
    
    **Returns:**
    - List of parking slots sorted by distance (closest first)
    - Real-time availability for each slot
    - Distance from your location in kilometers
    - Pricing information
    
    **Example:**
    ```
    GET /api/parking/public/nearby?latitude=8.5241&longitude=76.9366&radius_km=10
    ```
    """
    nearby_slots = await parking_service.find_nearby_parking_slots(
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        limit=limit
    )
    
    return [NearbySlotResponse(**slot) for slot in nearby_slots]


# ===== Parking Slot Endpoints =====

@router.post("/slot/create", description="Create a new parking slot")
async def create_parking_slot(
    user: UserDependency,
    parking_service: ParkingServiceDependency,
    slot_data: ParkingSlotCreate,
) -> ParkingSlotResponse:
    """
    Create a new parking slot. Status will be PENDING_VERIFICATION
    until approved by admin.
    """
    slot = await parking_service.create_slot(user.id, slot_data)
    return ParkingSlotResponse.model_validate(slot)


@router.get("/slot/list", description="List my parking slots")
async def list_my_slots(
    request: Request,
    user: UserDependency,
    parking_service: ParkingServiceDependency,
    pagination: PaginationParams,
    status: Optional[SlotStatus] = Query(None, description="Filter by status"),
) -> PaginatedResponse[ParkingSlotResponse]:
    """
    List all parking slots owned by the current user.
    """
    slots, total = await parking_service.list_my_slots(
        user.id,
        status=status,
        limit=pagination.limit,
        offset=pagination.offset
    )
    return paginated_response(
        result=[ParkingSlotResponse.model_validate(s) for s in slots],
        request=request,
        schema=ParkingSlotResponse
    )


@router.get("/staff/my-slots", description="List slots where I'm staff")
async def list_my_staff_slots(
    request: Request,
    user: UserDependency,
    parking_service: ParkingServiceDependency,
    pagination: PaginationParams,
    status: Optional[SlotStatus] = Query(None, description="Filter by status"),
) -> PaginatedResponse[ParkingSlotResponse]:
    """
    List all parking slots where the current user is staff (including owned slots).
    This includes slots where you are owner, staff, or volunteer.
    """
    slots, total = await parking_service.list_staff_slots(
        user.id,
        status=status,
        limit=pagination.limit,
        offset=pagination.offset
    )
    return paginated_response(
        result=[ParkingSlotResponse.model_validate(s) for s in slots],
        request=request,
        schema=ParkingSlotResponse
    )


@router.get("/slot/{slot_id}", description="Get parking slot details")
async def get_parking_slot(
    slot_id: UUID,
    parking_service: ParkingServiceDependency,
) -> ParkingSlotResponse:
    """
    Get detailed information about a specific parking slot.
    """
    slot = await parking_service.get_slot(slot_id)
    return ParkingSlotResponse.model_validate(slot)


@router.put("/slot/{slot_id}", description="Update parking slot")
async def update_parking_slot(
    slot_id: UUID,
    user: UserDependency,
    parking_service: ParkingServiceDependency,
    slot_data: ParkingSlotUpdate,
) -> ParkingSlotResponse:
    """
    Update parking slot details. Owner only.
    Cannot update active slots without deactivating first.
    """
    slot = await parking_service.update_slot(slot_id, user.id, slot_data)
    return ParkingSlotResponse.model_validate(slot)


@router.delete("/slot/{slot_id}", description="Delete parking slot")
async def delete_parking_slot(
    slot_id: UUID,
    user: UserDependency,
    parking_service: ParkingServiceDependency,
) -> MessageResponse:
    """
    Soft delete a parking slot. Owner only.
    Cannot delete if there are active parking sessions.
    """
    await parking_service.delete_slot(slot_id, user.id)
    return MessageResponse(message="Parking slot deleted successfully")


@router.get("/slot/{slot_id}/availability", description="Get live availability")
async def get_slot_availability(
    slot_id: UUID,
    parking_service: ParkingServiceDependency,
) -> SlotAvailability:
    """
    Get real-time availability showing occupied and available spaces
    by vehicle type.
    """
    return await parking_service.get_slot_availability(slot_id)


# ===== Admin Verification Endpoints =====

@router.get("/admin/pending-slots", description="List pending verification slots")
async def list_pending_slots(
    request: Request,
    admin: AdminUserDependency,
    parking_service: ParkingServiceDependency,
    pagination: PaginationParams,
) -> PaginatedResponse[ParkingSlotResponse]:
    """
    List all parking slots pending admin verification.
    Admin only.
    """
    slots, total = await parking_service.list_pending_slots(
        limit=pagination.limit,
        offset=pagination.offset
    )
    return paginated_response(
        result=[ParkingSlotResponse.model_validate(s) for s in slots],
        request=request,
        schema=ParkingSlotResponse
    )


@router.patch("/admin/slot/{slot_id}/verify", description="Verify or reject slot")
async def verify_parking_slot(
    slot_id: UUID,
    admin: AdminUserDependency,
    parking_service: ParkingServiceDependency,
    verification: SlotVerification,
) -> ParkingSlotResponse:
    """
    Approve or reject a parking slot.
    Admin only.
    """
    slot = await parking_service.verify_slot(slot_id, admin.id, verification)
    return ParkingSlotResponse.model_validate(slot)


# ===== Staff Management Endpoints =====

@router.post("/slot/{slot_id}/staff/add")
async def add_staff_member(
    slot_id: UUID,
    user: UserDependency,
    parking_service: EnhancedParkingServiceDependency,
    staff_data: StaffAdd,
):
    # Service method name makes role requirement clear
    staff = await parking_service.add_staff_as_owner(
        slot_id=slot_id,
        user_id=user.id, 
        staff_data=staff_data
    )
    return StaffResponse.model_validate(staff)


# NEW: Add staff by email
@router.post("/slot/{slot_id}/staff/add-by-email", description="Add staff member by email")
async def add_staff_by_email(
    slot_id: UUID,
    user: UserDependency,
    parking_service: ParkingServiceDependency,
    staff_data: StaffAddByEmail,
) -> StaffResponse:
    """
    Add a user as staff or volunteer to this parking slot by email address.
    
    **Owner only.**
    
    The user must already be registered in the system. If not, an error will be returned
    asking them to register first.
    
    **Parameters:**
    - email: Email address of the user to add
    - role: Role for this staff member (STAFF or VOLUNTEER)
    
    **Returns:**
    - Staff record with user details
    
    **Errors:**
    - USER_NOT_FOUND: No user found with that email
    - OWNER_AS_STAFF: Cannot add owner as staff
    - ALREADY_STAFF: User is already staff for this slot
    
    **Example:**
    ```json
    POST /api/parking/slot/{slot_id}/staff/add-by-email
    {
      "email": "staff@example.com",
      "role": "staff"
    }
    ```
    """
    staff = await parking_service.add_staff_by_email(slot_id, user.id, staff_data)
    return StaffResponse.model_validate(staff)


@router.delete("/slot/{slot_id}/staff/{staff_user_id}", description="Remove staff member")
async def remove_staff_member(
    slot_id: UUID,
    staff_user_id: UUID,
    user: UserDependency,
    parking_service: ParkingServiceDependency,
) -> MessageResponse:
    """
    Remove a staff member from this parking slot.
    Owner only. Cannot remove owner.
    """
    await parking_service.remove_staff(slot_id, staff_user_id, user.id)
    return MessageResponse(message="Staff member removed successfully")


@router.get("/slot/{slot_id}/staff/list", description="List staff members")
async def list_staff_members(
    slot_id: UUID,
    user: UserDependency,
    parking_service: ParkingServiceDependency,
) -> list[StaffResponse]:
    """
    List all staff members for this parking slot.
    Any staff member can view.
    """
    staff = await parking_service.list_staff(slot_id, user.id)
    return [StaffResponse.model_validate(s) for s in staff]


# ===== Session Management Endpoints =====

@router.post("/session/check-in", description="Check in a vehicle (ENHANCED)")
async def check_in_vehicle(
    user: UserDependency,
    parking_service: ParkingServiceDependency,
    slot_id: UUID = Query(..., description="Parking slot ID"),
    check_in_data: SessionCheckIn = ...,
) -> SessionWithDueAlert:
    """
    Check in a vehicle to a parking slot.
    
    **ENHANCED:** Now automatically links session to vehicle owner if the vehicle
    is registered in the system. This enables vehicle owners to see their parking
    history automatically.
    
    **Staff only.** Returns session and alerts if vehicle has outstanding dues.
    
    **Parameters:**
    - slot_id: Parking slot ID where vehicle is checking in
    - vehicle_number: Vehicle registration number
    - vehicle_type: Type of vehicle (car, bike, truck)
    - notes: Optional notes about the check-in
    
    **Returns:**
    - Parking session details (now includes vehicle_owner_id if registered)
    - Alert if vehicle has outstanding dues with this parking slot owner
    
    **Errors:**
    - SLOT_NOT_ACTIVE: Parking slot is not active
    - ALREADY_CHECKED_IN: Vehicle is already checked in elsewhere
    - CAPACITY_FULL: No available capacity for this vehicle type
    
    **Example:**
    ```json
    POST /api/parking/session/check-in?slot_id={uuid}
    {
      "vehicle_number": "KL01AB1234",
      "vehicle_type": "car",
      "notes": "Customer parked in slot A-10"
    }
    ```
    """
    session, due = await parking_service.check_in_vehicle(
        slot_id,
        user.id,
        check_in_data
    )
    
    response = SessionWithDueAlert.model_validate(session)
    
    if due:
        response.has_outstanding_due = True
        response.due_amount = due.due_amount - due.paid_amount
        response.due_id = due.id
    
    return response


@router.post("/session/calculate-fee", description="Calculate parking fee")
async def calculate_parking_fee(
    user: UserDependency,
    parking_service: ParkingServiceDependency,
    session_id: Optional[UUID] = None,
    vehicle_number: Optional[str] = Query(None, description="Vehicle number (alternative to session_id)"),
    slot_id: Optional[UUID] = Query(None, description="Slot ID (required with vehicle_number)"),
) -> dict:
    """
    Calculate the parking fee for a checked-in vehicle before checkout.
    
    **Enhanced:** Now supports calculation by either:
    - Session ID (traditional way)
    - Vehicle number + Slot ID (new way for easier staff operations)
    
    Shows current calculated fee based on time elapsed.
    Staff only.
    """
    fee_calculation = await parking_service.calculate_fee(
        session_id=session_id,
        vehicle_number=vehicle_number,
        slot_id=slot_id,
        staff_id=user.id
    )
    return fee_calculation


@router.post("/session/check-out", description="Check out a vehicle")
async def check_out_vehicle(
    user: UserDependency,
    parking_service: ParkingServiceDependency,
    check_out_data: SessionCheckOut,
    session_id: Optional[UUID] = None,
    vehicle_number: Optional[str] = Query(None, description="Vehicle number (alternative to session_id)"),
    slot_id: Optional[UUID] = Query(None, description="Slot ID (required with vehicle_number)"),
) -> SessionResponse:
    """
    Check out a vehicle and collect payment.
    
    **Enhanced:** Now supports checkout by either:
    - Session ID (traditional way)
    - Vehicle number + Slot ID (new way for easier staff operations)
    
    Staff only.
    """
    session = await parking_service.check_out_vehicle(
        staff_id=user.id,
        check_out_data=check_out_data,
        session_id=session_id,
        vehicle_number=vehicle_number,
        slot_id=slot_id
    )
    return SessionResponse.model_validate(session)


@router.post("/session/escape", description="Mark vehicle as escaped")
async def mark_vehicle_escaped(
    user: UserDependency,
    parking_service: ParkingServiceDependency,
    session_id: Optional[UUID] = None,
    vehicle_number: Optional[str] = Query(None, description="Vehicle number (alternative to session_id)"),
    slot_id: Optional[UUID] = Query(None, description="Slot ID (required with vehicle_number)"),
) -> dict:
    """
    Mark a vehicle as escaped (left without paying).
    
    **Enhanced:** Now supports marking escape by either:
    - Session ID (traditional way)
    - Vehicle number + Slot ID (new way for easier staff operations)
    
    Creates a due record automatically.
    Staff only.
    """
    session, due = await parking_service.mark_escaped(
        staff_id=user.id,
        session_id=session_id,
        vehicle_number=vehicle_number,
        slot_id=slot_id
    )
    
    return {
        "session": SessionResponse.model_validate(session),
        "due": DueResponse.model_validate(due)
    }


@router.get("/session/list", description="List parking sessions")
async def list_parking_sessions(
    request: Request,
    user: UserDependency,
    parking_service: ParkingServiceDependency,
    pagination: PaginationParams,
    slot_id: UUID = Query(..., description="Parking slot ID"),
    status: Optional[SessionStatus] = Query(None, description="Filter by status"),
) -> PaginatedResponse[SessionResponse]:
    """
    List parking sessions for a specific slot.
    Staff only. Returns paginated results.
    """
    sessions, total = await parking_service.list_sessions(
        slot_id,
        user.id,
        status=status,
        limit=pagination.limit,
        offset=pagination.offset
    )
    return paginated_response(
        result=[SessionResponse.model_validate(s) for s in sessions],
        request=request,
        schema=SessionResponse
    )


# ===== NEW: Vehicle Transaction History Endpoints =====

@router.get("/vehicle/{vehicle_number}/history", description="Get vehicle transaction history")
async def get_vehicle_history(
    request: Request,
    vehicle_number: str,
    user: UserDependency,
    parking_service: ParkingServiceDependency,
    pagination: PaginationParams,
) -> VehicleTransactionHistory:
    """
    Get complete parking transaction history for a specific vehicle.
    
    Shows all parking sessions (completed, active, escaped) and outstanding dues
    for the given vehicle number across all parking slots.
    
    **Authentication required.**
    
    **Parameters:**
    - vehicle_number: Vehicle registration number to look up
    - limit: Maximum records to return (default: 100)
    - offset: Pagination offset
    
    **Returns:**
    - Complete transaction history including:
      - All parking sessions with dates, locations, fees
      - Total amount spent
      - Active parking sessions
      - Outstanding dues
      - Whether vehicle is registered to requesting user
    
    **Use Cases:**
    - Vehicle owners checking their own parking history
    - Staff looking up a vehicle's payment history
    - Anyone can search any vehicle number
    
    **Example:**
    ```
    GET /api/parking/vehicle/KL01AB1234/history?limit=50&offset=0
    ```
    """
    history = await parking_service.get_vehicle_transaction_history(
        vehicle_number=vehicle_number,
        requesting_user_id=user.id,
        limit=pagination.limit,
        offset=pagination.offset
    )
    return history


@router.get("/my-vehicles/history", description="Get my vehicles' parking history")
async def get_my_vehicles_history(
    user: UserDependency,
    parking_service: ParkingServiceDependency,
) -> dict:
    """
    Get parking transaction history for ALL vehicles registered to the current user.
    
    **Authentication required.**
    
    **Returns:**
    - Summary of all registered vehicles with:
      - Total sessions per vehicle
      - Total spent per vehicle
      - Active sessions per vehicle
      - Outstanding dues per vehicle
    - Overall totals across all vehicles
    
    **Note:** Only shows vehicles that are registered in the system and linked to your account.
    If you want to check an unregistered vehicle, use the `/vehicle/{vehicle_number}/history` endpoint.
    
    **Example:**
    ```
    GET /api/parking/my-vehicles/history
    ```
    
    **Sample Response:**
    ```json
    {
      "total_vehicles": 2,
      "total_sessions": 45,
      "total_spent": 2350.00,
      "outstanding_dues": 150.00,
      "vehicles": [
        {
          "vehicle_id": "uuid",
          "vehicle_number": "KL01AB1234",
          "vehicle_name": "My Car",
          "vehicle_type": "car",
          "total_sessions": 30,
          "total_spent": 1500.00,
          "active_sessions": 1,
          "outstanding_dues": 0.00
        }
      ]
    }
    ```
    """
    history = await parking_service.get_my_vehicles_history(user_id=user.id)
    return history


@router.get("/staff/vehicle-lookup", description="Quick vehicle lookup for staff")
async def staff_vehicle_lookup(
    vehicle_number: str = Query(..., description="Vehicle number to look up"),
    user: UserDependency = ...,
    parking_service: ParkingServiceDependency = ...,
) -> dict:
    """
    Quick vehicle lookup for staff members.
    
    Returns basic info about a vehicle:
    - Is it registered?
    - Does it have outstanding dues?
    - Recent parking history (last 5 sessions)
    
    **Authentication required.**
    
    **Use Case:**
    - Staff at check-in can quickly see if a vehicle has unpaid dues
    - Staff can see recent parking history before accepting the vehicle
    
    **Example:**
    ```
    GET /api/parking/staff/vehicle-lookup?vehicle_number=KL01AB1234
    ```
    
    **Sample Response:**
    ```json
    {
      "vehicle_number": "KL01AB1234",
      "is_registered": true,
      "has_outstanding_dues": true,
      "outstanding_dues": 150.00,
      "total_sessions": 25,
      "recent_sessions": [
        {
          "slot_name": "Downtown Parking",
          "check_in": "2025-01-10T14:30:00Z",
          "check_out": null,
          "status": "escaped",
          "fee": 150.00
        }
      ]
    }
    ```
    """
    # Get last 5 sessions only
    history = await parking_service.get_vehicle_transaction_history(
        vehicle_number=vehicle_number,
        requesting_user_id=user.id,
        limit=5,
        offset=0
    )
    
    return {
        "vehicle_number": history.vehicle_number,
        "is_registered": history.is_registered,
        "has_outstanding_dues": history.outstanding_dues > 0,
        "outstanding_dues": float(history.outstanding_dues),
        "total_sessions": history.total_sessions,
        "recent_sessions": [
            {
                "slot_name": t.slot.name,
                "check_in": t.check_in_time,
                "check_out": t.check_out_time,
                "status": t.status.value if hasattr(t.status, 'value') else t.status,
                "fee": float(t.collected_fee if t.collected_fee else t.calculated_fee)
            }
            for t in history.transactions[:5]
        ]
    }


# ===== Due Management Endpoints =====

@router.patch("/due/{due_id}/collect", description="Collect payment for due")
async def collect_due_payment(
    due_id: UUID,
    user: UserDependency,
    parking_service: ParkingServiceDependency,
    payment_data: DueCollect,
) -> DueResponse:
    """
    Collect payment for an outstanding vehicle due.
    Staff only (must belong to slot owner).
    """
    due = await parking_service.collect_due_payment(due_id, user.id, payment_data)
    return DueResponse.model_validate(due)


@router.get("/due/list", description="List vehicle dues")
async def list_vehicle_dues(
    request: Request,
    user: UserDependency,
    parking_service: ParkingServiceDependency,
    pagination: PaginationParams,
    status: Optional[DueStatus] = Query(None, description="Filter by status"),
) -> PaginatedResponse[DueResponse]:
    """
    List all vehicle dues for parking slots owned by current user.
    Owner only.
    """
    dues, total = await parking_service.list_dues(
        user.id,
        status=status,
        limit=pagination.limit,
        offset=pagination.offset
    )
    return paginated_response(
        result=[DueResponse.model_validate(d) for d in dues],
        request=request,
        schema=DueResponse
    )


# ===== Analytics Endpoints =====

@router.get("/analytics/dashboard", description="Get analytics dashboard")
async def get_analytics_dashboard(
    user: UserDependency,
    parking_service: ParkingServiceDependency,
    start_date: Optional[datetime] = Query(
        None,
        description="Start date (defaults to today)"
    ),
    end_date: Optional[datetime] = Query(
        None,
        description="End date (defaults to now)"
    ),
) -> dict:
    """
    Get analytics dashboard for slot owner.
    Shows revenue, sessions, and dues breakdown.
    Owner only.
    
    **Not yet implemented** — returns 501.
    """
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=501,
        content={
            "detail": "Analytics dashboard not yet implemented",
            "error_code": "NOT_IMPLEMENTED"
        }
    )


@router.get("/my-workplaces")
async def get_my_workplaces(
    user: UserDependency,
    parking_service: EnhancedParkingServiceDependency,
):
    """
    Show all slots where I have access, grouped by role.
    Helps users understand their different contexts.
    """
    roles = await parking_service.role_manager.get_all_user_slot_roles(
        user_id=user.id,
        status_filter=SlotStatus.ACTIVE
    )
    
    owned = [r for r in roles if r.is_owner]
    staff = [r for r in roles if r.is_staff]
    
    return {
        "owned_slots": [
            {
                "slot_id": r.slot_id,
                "slot_name": r.slot_name,
                "role": r.role.value,
                "permissions": {
                    "can_manage_staff": r.can_manage_staff,
                    "can_check_in_out": r.can_check_in_out,
                    "can_view_analytics": r.can_view_analytics
                }
            } for r in owned
        ],
        "staff_slots": [
            {
                "slot_id": r.slot_id,
                "slot_name": r.slot_name,
                "role": r.role.value,
                "owner_id": r.slot_owner_id,
                "permissions": {
                    "can_manage_staff": r.can_manage_staff,
                    "can_check_in_out": r.can_check_in_out,
                    "can_view_analytics": r.can_view_analytics
                }
            } for r in staff
        ],
        "summary": {
            "total_slots": len(roles),
            "as_owner": len(owned),
            "as_staff": len(staff)
        }
    }

@router.get("/my-role/{slot_id}")
async def get_my_role_in_slot(
    slot_id: UUID,
    user: UserDependency,
    parking_service: EnhancedParkingServiceDependency,
):
    """
    Check what role I have in a specific slot.
    Useful for UI to show/hide features.
    """
    role = await parking_service.role_manager.get_user_role_for_slot(
        user_id=user.id,
        slot_id=slot_id
    )
    
    if not role:
        raise ForbiddenException("You don't have access to this parking slot")
    
    return {
        "slot_id": role.slot_id,
        "slot_name": role.slot_name,
        "your_role": role.role.value,
        "is_owner": role.is_owner,
        "permissions": {
            "can_manage_staff": role.can_manage_staff,
            "can_check_in_out": role.can_check_in_out,
            "can_collect_dues": role.can_collect_dues,
            "can_view_analytics": role.can_view_analytics
        }
    }

@router.get("/admin/analytics", description="Get master analytics")
async def get_admin_analytics(
    admin: AdminUserDependency,
    parking_service: ParkingServiceDependency,
    start_date: Optional[datetime] = Query(
        None,
        description="Start date (defaults to today)"
    ),
    end_date: Optional[datetime] = Query(
        None,
        description="End date (defaults to now)"
    ),
) -> dict:
    """
    Get master analytics dashboard for all parking slots.
    Admin only.
    """
    analytics = await parking_service.get_admin_analytics(start_date, end_date)
    return analytics