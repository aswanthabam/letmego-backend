# apps/api/apartment/router.py

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Query

from apps.api.auth.dependency import AdminUserDependency
from apps.api.apartment.dependency import ApartmentAdminDependency
from apps.api.apartment.service import ApartmentServiceDependency
from apps.api.apartment.schema import (
    ApartmentCreate,
    ApartmentUpdate,
    ApartmentResponse,
    PermittedVehicleCreate,
    PermittedVehicleUpdate,
    PermittedVehicleResponse,
    VehiclePermissionCheckResponse,
)
from avcfastapi.core.fastapi.response.models import MessageResponse
from avcfastapi.core.fastapi.response.pagination import (
    PaginatedResponse,
    PaginationParams,
    paginated_response,
)

router = APIRouter(
    prefix="/apartment",
    tags=["Apartment Management"],
)


# ===== Apartment CRUD (Super Admin only) =====


@router.post("/create", description="Create a new apartment (Super Admin only)")
async def create_apartment(
    admin: AdminUserDependency,
    apartment_service: ApartmentServiceDependency,
    apartment_data: ApartmentCreate,
) -> ApartmentResponse:
    """
    Create a new apartment and assign an admin to manage it.
    Only accessible by super admin users.
    """
    apartment = await apartment_service.create_apartment(apartment_data)
    return ApartmentResponse.model_validate(apartment)


@router.get("/list", description="Get list of all apartments (Super Admin only)")
async def get_all_apartments(
    admin: AdminUserDependency,
    apartment_service: ApartmentServiceDependency,
    pagination: PaginationParams,
) -> PaginatedResponse[ApartmentResponse]:
    """
    Get paginated list of all apartments.
    Only accessible by super admin users.
    """
    apartments, total = await apartment_service.get_all_apartments(
        skip=pagination.offset,
        limit=pagination.limit,
    )
    return paginated_response(
        result=[ApartmentResponse.model_validate(apt) for apt in apartments],
        request=pagination.request,
        schema=ApartmentResponse,
    )


@router.get("/my-apartments", description="Get apartments managed by current admin")
async def get_my_apartments(
    apartment_admin: ApartmentAdminDependency,
    apartment_service: ApartmentServiceDependency,
) -> list[ApartmentResponse]:
    """
    Get all apartments managed by the current apartment admin.
    """
    apartments = await apartment_service.get_apartments_by_admin(apartment_admin.id)
    return [ApartmentResponse.model_validate(apt) for apt in apartments]


@router.get("/{apartment_id}", description="Get apartment details")
async def get_apartment(
    apartment_admin: ApartmentAdminDependency,
    apartment_service: ApartmentServiceDependency,
    apartment_id: UUID,
) -> ApartmentResponse:
    """
    Get detailed information about a specific apartment.
    """
    apartment = await apartment_service.get_apartment(apartment_id)
    if not apartment:
        from avcfastapi.core.exception.request import InvalidRequestException

        raise InvalidRequestException(
            "Apartment not found", error_code="APARTMENT_NOT_FOUND"
        )

    # Verify admin has access to this apartment
    if apartment_admin.role != "admin":  # Super admin can access all
        apartment_service.verify_apartment_admin(apartment, apartment_admin.id)

    return ApartmentResponse.model_validate(apartment)


@router.put(
    "/{apartment_id}", description="Update apartment details (Super Admin only)"
)
async def update_apartment(
    admin: AdminUserDependency,
    apartment_service: ApartmentServiceDependency,
    apartment_id: UUID,
    apartment_data: ApartmentUpdate,
) -> ApartmentResponse:
    """
    Update an apartment's details.
    Only accessible by super admin users.
    """
    apartment = await apartment_service.update_apartment(apartment_id, apartment_data)
    return ApartmentResponse.model_validate(apartment)


@router.delete("/{apartment_id}", description="Delete an apartment (Super Admin only)")
async def delete_apartment(
    admin: AdminUserDependency,
    apartment_service: ApartmentServiceDependency,
    apartment_id: UUID,
) -> MessageResponse:
    """
    Soft delete an apartment.
    Only accessible by super admin users.
    """
    await apartment_service.delete_apartment(apartment_id)
    return MessageResponse(message="Apartment deleted successfully")


# ===== Permitted Vehicle Management (Apartment Admin) =====


@router.post(
    "/{apartment_id}/vehicles/add",
    description="Add a vehicle to permitted parking list",
)
async def add_permitted_vehicle(
    apartment_admin: ApartmentAdminDependency,
    apartment_service: ApartmentServiceDependency,
    apartment_id: UUID,
    vehicle_data: PermittedVehicleCreate,
) -> PermittedVehicleResponse:
    """
    Add a vehicle to the apartment's permitted parking list.
    Only accessible by the apartment's admin.
    """
    permitted_vehicle = await apartment_service.add_permitted_vehicle(
        apartment_id=apartment_id,
        vehicle_data=vehicle_data,
        admin_id=apartment_admin.id,
    )
    return PermittedVehicleResponse.model_validate(permitted_vehicle)


@router.delete(
    "/{apartment_id}/vehicles/{vehicle_id}",
    description="Remove a vehicle from permitted parking list",
)
async def remove_permitted_vehicle(
    apartment_admin: ApartmentAdminDependency,
    apartment_service: ApartmentServiceDependency,
    apartment_id: UUID,
    vehicle_id: UUID,
) -> MessageResponse:
    """
    Remove a vehicle from the apartment's permitted parking list.
    Only accessible by the apartment's admin.
    """
    await apartment_service.remove_permitted_vehicle(
        apartment_id=apartment_id,
        vehicle_id=vehicle_id,
        admin_id=apartment_admin.id,
    )
    return MessageResponse(message="Vehicle removed from permitted list successfully")


@router.get(
    "/{apartment_id}/vehicles/check/{vehicle_id}",
    description="Check if a vehicle is permitted",
)
async def check_vehicle_permission(
    apartment_admin: ApartmentAdminDependency,
    apartment_service: ApartmentServiceDependency,
    apartment_id: UUID,
    vehicle_id: UUID,
) -> VehiclePermissionCheckResponse:
    """
    Check if a vehicle is permitted in the apartment's parking.
    Only accessible by the apartment's admin.
    """
    permission = await apartment_service.check_vehicle_permission(
        apartment_id=apartment_id,
        vehicle_id=vehicle_id,
        admin_id=apartment_admin.id,
    )

    if permission:
        return VehiclePermissionCheckResponse(
            is_permitted=True,
            apartment_id=permission.apartment_id,
            apartment_name=permission.apartment.name if permission.apartment else None,
            parking_spot=permission.parking_spot,
            notes=permission.notes,
        )
    else:
        return VehiclePermissionCheckResponse(is_permitted=False)


@router.get(
    "/{apartment_id}/vehicles/list",
    description="Get all permitted vehicles for an apartment",
)
async def get_permitted_vehicles(
    apartment_admin: ApartmentAdminDependency,
    apartment_service: ApartmentServiceDependency,
    apartment_id: UUID,
    pagination: PaginationParams,
) -> PaginatedResponse[PermittedVehicleResponse]:
    """
    Get paginated list of all vehicles permitted in the apartment's parking.
    Only accessible by the apartment's admin.
    """
    vehicles, total = await apartment_service.get_permitted_vehicles(
        apartment_id=apartment_id,
        admin_id=apartment_admin.id,
        skip=pagination.offset,
        limit=pagination.limit,
    )
    return paginated_response(
        result=[PermittedVehicleResponse.model_validate(v) for v in vehicles],
        request=pagination.request,
        schema=PermittedVehicleResponse,
    )
