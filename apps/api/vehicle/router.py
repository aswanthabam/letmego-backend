from typing import List
from fastapi import APIRouter

from apps.api.auth.dependency import UserDependency
from core.db.core import SessionDep
from apps.api.vehicle.schema import (
    CreateVehicleRequest,
    UpdateVehicleRequest,
    VehicleResponse,
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


@router.post("/create", description="Create a new vehicle")
async def create_vehicle_endpoint(
    session: SessionDep,
    user: UserDependency,
    create_vehicle_request: CreateVehicleRequest,
) -> VehicleResponse:
    vehicle = await create_vehicle(
        session=session,
        vehicle_number=create_vehicle_request.vehicle_number,
        user_id=user.id,
        name=create_vehicle_request.name,
        is_verified=False,
    )
    return vehicle


@router.put("/update/{id}", description="Update an existing vehicle")
async def update_vehicle_endpoint(
    session: SessionDep,
    user: UserDependency,
    id: str,
    update_vehicle_request: UpdateVehicleRequest,
) -> VehicleResponse:
    vehicle = await update_vehicle(
        session=session,
        vehicle_id=id,
        user_id=user.id,
        vehicle_number=update_vehicle_request.vehicle_number,
        name=update_vehicle_request.name,
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
