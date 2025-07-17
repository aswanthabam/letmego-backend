# apps/vehicle/router.py
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, File, UploadFile, Form

from apps.api.auth.dependency import UserDependency
from apps.api.vehicle.service import VehicleServiceDependency
from apps.api.vehicle.schema import (
    FuelType,
    FuelTypeResponse,
    VehicleDetailResponse,
    VehicleResponseMin,
    VehicleType,
    VehicleTypeResponse,
)
from core.response.models import MessageResponse

router = APIRouter(
    prefix="/vehicle",
    tags=["Vehicle"],
)


@router.get("/types", description="Get all vehicle types")
async def get_vehicle_types() -> List[VehicleTypeResponse]:
    """Get all available vehicle types"""
    return [
        VehicleTypeResponse(value=vt.value, display_name=vt.display_text)
        for vt in VehicleType
    ]


@router.get("/fuel-types", description="Get all vehicle types")
async def get_vehicle_types() -> List[VehicleTypeResponse]:
    """Get all available vehicle types"""
    return [
        FuelTypeResponse(value=vt.value, display_name=vt.display_text)
        for vt in FuelType
    ]


@router.post("/create", description="Create a new vehicle")
async def create_vehicle_endpoint(
    user: UserDependency,
    vehicle_service: VehicleServiceDependency,
    name: str = Form(None),
    vehicle_number: str = Form(...),
    vehicle_type: VehicleType = Form(None),
    fuel_type: FuelType = Form(None),
    brand: str = Form(None),
    image: Optional[UploadFile] = File(None),
) -> VehicleResponseMin:
    vehicle = await vehicle_service.create_vehicle(
        vehicle_number=vehicle_number,
        user_id=user.id,
        name=name,
        vehicle_type=vehicle_type.value if vehicle_type else None,
        fuel_type=fuel_type.value if fuel_type else None,
        brand=brand,
        image=image,
        is_verified=False,
    )
    return vehicle


@router.put("/update/{id}", description="Update an existing vehicle")
async def update_vehicle_endpoint(
    user: UserDependency,
    vehicle_service: VehicleServiceDependency,
    id: str,
    name: str = Form(None),
    vehicle_number: str = Form(...),
    vehicle_type: VehicleType = Form(None),
    fuel_type: FuelType = Form(None),
    brand: str = Form(None),
    image: UploadFile = File(None),
) -> VehicleResponseMin:
    vehicle = await vehicle_service.update_vehicle(
        vehicle_id=id,
        user_id=user.id,
        vehicle_number=vehicle_number,
        name=name,
        vehicle_type=vehicle_type.value if vehicle_type else None,
        fuel_type=fuel_type.value if fuel_type else None,
        brand=brand,
        image=image,
    )
    return vehicle


@router.get("/get/{id}", description="Get vehicle details by ID")
async def get_vehicle_endpoint(
    vehicle_service: VehicleServiceDependency, user: UserDependency, id: str
) -> VehicleDetailResponse:
    try:
        val = UUID(id, version=4)
        if str(val) == id and val.version == 4:
            return await vehicle_service.get_vehicle(vehicle_id=id)
    except ValueError:
        pass
    return await vehicle_service.get_vehicle(vehicle_number=id)


@router.get("/list", description="For listing all vehicles user ownes")
async def list_vehicles_endpoint(
    vehicle_service: VehicleServiceDependency,
    user: UserDependency,
    vehicle_type: Optional[VehicleType] = None,
    search_term: Optional[str] = None,
    fuel_type: Optional[FuelType] = None,
) -> List[VehicleResponseMin]:
    return await vehicle_service.get_vehicles(
        user_id=user.id,
        vehicle_type=vehicle_type.value if vehicle_type else None,
        fuel_type=fuel_type.value if fuel_type else None,
        search_term=search_term,
    )


@router.get("/search", description="Search vehicles")
async def search_vehicles_endpoint(
    vehicle_service: VehicleServiceDependency,
    user: UserDependency,
    vehicle_number: str,
    limit: int = 10,
    offset: int = 0,
) -> List[VehicleResponseMin]:
    """
    Search for vehicles by vehicle number.
    """
    return await vehicle_service.search_vehicle_number(
        vehicle_number=vehicle_number,
        limit=limit,
        offset=offset,
    )


@router.delete("/delete/{id}", description="Delete vehicle")
async def delete_vehicle_endpoint(
    vehicle_service: VehicleServiceDependency, user: UserDependency, id: str
) -> MessageResponse:
    await vehicle_service.delete_vehicle(vehicle_id=id, user_id=user.id)
    return {"message": "Vehicle deleted successfully"}
