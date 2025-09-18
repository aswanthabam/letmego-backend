# apps/vehicle/router.py
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, File, Request, UploadFile, Form
from fastapi.responses import RedirectResponse

from apps.api.auth.dependency import UserDependency
from apps.api.vehicle.models import VehicleLocationVisibility
from apps.api.vehicle.service import VehicleServiceDependency
from apps.api.vehicle.schema import (
    FuelType,
    FuelTypeResponse,
    VehicleDetailResponse,
    VehicleLocationDetail,
    VehicleResponseMin,
    VehicleType,
    VehicleTypeResponse,
)
from avcfastapi.core.fastapi.response.models import MessageResponse
from avcfastapi.core.fastapi.response.pagination import (
    PaginatedResponse,
    PaginationParams,
    paginated_response,
)
from avcfastapi.core.utils.validations.uuid import is_valid_uuid

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
    if is_valid_uuid(id):
        return await vehicle_service.get_vehicle(vehicle_id=id)
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
    request: Request,
    vehicle_service: VehicleServiceDependency,
    user: UserDependency,
    vehicle_number: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    limit: int = 10,
    offset: int = 0,
) -> List[VehicleResponseMin]:
    """
    Search for vehicles by vehicle number.
    """
    response = await vehicle_service.search_vehicle_number(
        vehicle_number=vehicle_number,
        limit=limit,
        offset=offset,
    )
    ip_address = request.client.host if request.client else None
    await vehicle_service.log_search_term(
        user_id=user.id,
        search_term=vehicle_number,
        status=len(response) > 0 and "success" or "not_found",
        latitude=latitude,
        longitude=longitude,
        ip_address=ip_address,
        result_count=len(response),
    )
    return response


@router.delete("/delete/{id}", description="Delete vehicle")
async def delete_vehicle_endpoint(
    vehicle_service: VehicleServiceDependency, user: UserDependency, id: str
) -> MessageResponse:
    await vehicle_service.delete_vehicle(vehicle_id=id, user_id=user.id)
    return {"message": "Vehicle deleted successfully"}


@router.post("/location/add", description="Add a new vehicle location")
async def add_vehicle_location_endpoint(
    user: UserDependency,
    vehicle_service: VehicleServiceDependency,
    vehicle_id: UUID = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    notes: str = Form(None),
    image: UploadFile = File(None),
    visibility: VehicleLocationVisibility = Form(
        VehicleLocationVisibility.PRIVATE.value
    ),
) -> VehicleLocationDetail:
    location = await vehicle_service.save_vehicle_location(
        vehicle_id=vehicle_id,
        user_id=user.id,
        latitude=latitude,
        longitude=longitude,
        notes=notes,
        image=image,
        visibility=visibility,
    )
    location = await vehicle_service.get_vehicle_location(
        vehicle_location_id=location.id, user_id=user.id
    )
    return location


@router.patch(
    "/location/change-visibility/{vehicle_location_id}",
    description="Change vehicle location visibility",
)
async def change_vehicle_location_visibility_endpoint(
    vehicle_service: VehicleServiceDependency,
    user: UserDependency,
    vehicle_location_id: str,
    visibility: VehicleLocationVisibility = Form(...),
) -> VehicleLocationDetail:
    await vehicle_service.change_vehicle_location_visibility(
        vehicle_location_id=vehicle_location_id, user_id=user.id, visibility=visibility
    )
    return await vehicle_service.get_vehicle_location(
        vehicle_location_id=vehicle_location_id, user_id=user.id
    )


@router.get("/location/get/{vehicle_location_id}", description="Get vehicle locations")
async def get_vehicle_locations_endpoint(
    vehicle_service: VehicleServiceDependency, vehicle_location_id: str
) -> VehicleLocationDetail:
    # currently only public locations are returned
    return await vehicle_service.get_vehicle_location(
        vehicle_location_id=vehicle_location_id, user_id=None
    )


@router.get("/location/list", description="List vehicle locations")
async def list_vehicle_locations_endpoint(
    request: Request,
    vehicle_service: VehicleServiceDependency,
    pagination: PaginationParams,
    user: UserDependency,
    vehicle_id: Optional[str] = None,
    visibility: Optional[VehicleLocationVisibility] = None,
) -> PaginatedResponse[VehicleLocationDetail]:
    result = await vehicle_service.list_vehicle_locations(
        user_id=user.id,
        vehicle_id=vehicle_id,
        visibility=visibility.value if visibility else None,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return paginated_response(
        request=request, result=result, schema=VehicleLocationDetail
    )


@router.delete(
    "/location/delete/{vehicle_location_id}", description="Delete vehicle location"
)
async def delete_vehicle_location_endpoint(
    vehicle_service: VehicleServiceDependency,
    user: UserDependency,
    vehicle_location_id: str,
) -> MessageResponse:
    await vehicle_service.delete_vehicle_location(
        vehicle_location_id=vehicle_location_id, user_id=user.id
    )
    return {"message": "Vehicle location deleted successfully"}


@router.get(
    "/location/redirect/{vehicle_location_id}",
    description="Redirect to corresponding page for vehicle location details",
)
async def redirect_to_vehicle_location_endpoint(
    vehicle_service: VehicleServiceDependency,
    vehicle_location_id: UUID,
):
    url = await vehicle_service.get_location_redirect_url(
        vehicle_location_id=vehicle_location_id
    )
    return RedirectResponse(url=url, status_code=303)
