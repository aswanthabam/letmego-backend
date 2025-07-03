# apps/vehicle/router.py
from typing import List, Optional
from fastapi import APIRouter, File, UploadFile, Form
from fastapi.params import Depends

from apps.api.auth.dependency import UserDependency
from core.db.core import SessionDep
from apps.api.vehicle.models import VehicleType
from apps.api.vehicle.schema import (
    CreateVehicleRequest,
    UpdateVehicleRequest,
    VehicleResponse,
    VehicleTypeResponse,
)
from apps.api.vehicle.service import (
    create_vehicle,
    get_vehicle,
    get_vehicles,
    update_vehicle,
    delete_vehicle,
)

router = APIRouter(
    prefix="/vehicle",
)


@router.get("/types", description="Get all vehicle types")
async def get_vehicle_types() -> List[VehicleTypeResponse]:
    """Get all available vehicle types"""
    return [
        VehicleTypeResponse(value=vt.value, display_name=vt.value) for vt in VehicleType
    ]


@router.post("/create", description="Create a new vehicle")
async def create_vehicle_endpoint(
    session: SessionDep,
    user: UserDependency,
    name: str = Form(None),
    vehicle_number: str = Form(...),
    vehicle_type: VehicleType = Form(None),
    brand: str = Form(None),
    image: Optional[UploadFile] = File(None),
) -> VehicleResponse:
    vehicle = await create_vehicle(
        session=session,
        vehicle_number=vehicle_number,
        user_id=user.id,
        name=name,
        vehicle_type=vehicle_type,
        brand=brand,
        image=image,
        is_verified=False,
    )
    return vehicle


@router.put("/update/{id}", description="Update an existing vehicle")
async def update_vehicle_endpoint(
    session: SessionDep,
    user: UserDependency,
    id: str,
    name: str = Form(None),
    vehicle_number: str = Form(...),
    vehicle_type: VehicleType = Form(None),
    brand: str = Form(None),
    image: UploadFile = File(None),
) -> VehicleResponse:
    vehicle = await update_vehicle(
        session=session,
        vehicle_id=id,
        user_id=user.id,
        vehicle_number=vehicle_number,
        name=name,
        vehicle_type=vehicle_type,
        brand=brand,
        image=image,
    )
    return vehicle


@router.get("/get/{id}", description="Get vehicle details by ID")
async def get_vehicle_endpoint(
    session: SessionDep, user: UserDependency, id: str
) -> VehicleResponse:
    return await get_vehicle(session=session, vehicle_id=id, user_id=user.id)


@router.get("/list", description="List vehicles")
async def list_vehicles_endpoint(
    session: SessionDep, user: UserDependency
) -> List[VehicleResponse]:
    return await get_vehicles(session=session, user_id=user.id)


@router.delete("/delete/{id}", description="Delete vehicle")
async def delete_vehicle_endpoint(session: SessionDep, user: UserDependency, id: str):
    await delete_vehicle(session=session, vehicle_id=id, user_id=user.id)
    return {}
