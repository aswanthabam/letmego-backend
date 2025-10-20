# apps/api/shop/router.py

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Query, Request

from apps.api.auth.dependency import AdminUserDependency
from apps.api.shop.service import ShopServiceDependency
from apps.api.shop.schema import ShopCreate, ShopUpdate, ShopResponse
from avcfastapi.core.fastapi.response.models import MessageResponse
from avcfastapi.core.fastapi.response.pagination import (
    PaginatedResponse,
    PaginationParams,
    paginated_response,
)

router = APIRouter(
    prefix="/shop",
    tags=["Shop Management"],
)


@router.post("/create", description="Create a new shop (Admin only)")
async def create_shop(
    admin: AdminUserDependency,
    shop_service: ShopServiceDependency,
    shop_data: ShopCreate,
) -> ShopResponse:
    """
    Create a new shop with location and other details.
    Only accessible by admin users.
    """
    shop = await shop_service.create_shop(shop_data)
    return ShopResponse.model_validate(shop)


@router.get("/list", description="Get list of shops")
async def get_shops(
    request: Request,
    shop_service: ShopServiceDependency,
    pagination: PaginationParams,
    category: Optional[str] = Query(None, description="Filter by category"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
) -> PaginatedResponse[ShopResponse]:
    """
    Get paginated list of shops with optional filters.
    """
    shops, total = await shop_service.get_shops(
        skip=pagination.offset,
        limit=pagination.limit,
        category=category,
        is_active=is_active,
    )
    return paginated_response(
        result=[ShopResponse.model_validate(shop) for shop in shops],
        request=request,
        schema=ShopResponse,
    )


@router.get("/{shop_id}", description="Get shop details by ID")
async def get_shop(
    shop_service: ShopServiceDependency,
    shop_id: UUID,
) -> ShopResponse:
    """
    Get detailed information about a specific shop.
    """
    shop = await shop_service.get_shop(shop_id)
    if not shop:
        from avcfastapi.core.exception.request import InvalidRequestException

        raise InvalidRequestException("Shop not found", error_code="SHOP_NOT_FOUND")
    return ShopResponse.model_validate(shop)


@router.put("/{shop_id}", description="Update shop details (Admin only)")
async def update_shop(
    admin: AdminUserDependency,
    shop_service: ShopServiceDependency,
    shop_id: UUID,
    shop_data: ShopUpdate,
) -> ShopResponse:
    """
    Update an existing shop's details.
    Only accessible by admin users.
    """
    shop = await shop_service.update_shop(shop_id, shop_data)
    return ShopResponse.model_validate(shop)


@router.delete("/{shop_id}", description="Delete a shop (Admin only)")
async def delete_shop(
    admin: AdminUserDependency,
    shop_service: ShopServiceDependency,
    shop_id: UUID,
) -> MessageResponse:
    """
    Soft delete a shop.
    Only accessible by admin users.
    """
    await shop_service.delete_shop(shop_id)
    return MessageResponse(message="Shop deleted successfully")
