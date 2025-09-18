from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Request, Query

from apps.api.admin.schema import (
    UserWithCountsSchema,
    VehicleReportSchema,
    VehicleSearchLogResponse,
    VehicleWithCountsSchema,
)
from apps.api.admin.service import AdminDashboardServiceDependency
from apps.api.auth.dependency import AdminUserDependency
from apps.api.vehicle.models import SearchTermStatus
from avcfastapi.core.fastapi.response.pagination import (
    PaginatedResponse,
    PaginationParams,
    paginated_response,
)

router = APIRouter(prefix="/admin")


@router.get("/statistics", description="Get admin statistics")
async def get_statistics(
    user: AdminUserDependency,
    admin_dashboard_service: AdminDashboardServiceDependency,
    from_date: datetime | None = Query(
        None, description="Filter from this datetime (inclusive, timezone-aware)"
    ),
    to_date: datetime | None = Query(
        None, description="Filter to this datetime (inclusive, timezone-aware)"
    ),
):
    total_users = await admin_dashboard_service.get_users_count(from_date, to_date)
    total_vehicles = await admin_dashboard_service.get_vehicles_count(
        from_date, to_date
    )
    total_reports = await admin_dashboard_service.get_reports_count(from_date, to_date)
    success_total_search_terms = await admin_dashboard_service.count_search_logs(
        from_date=from_date, to_date=to_date, status=SearchTermStatus.SUCCESS
    )
    not_found_total_search_terms = await admin_dashboard_service.count_search_logs(
        from_date=from_date, to_date=to_date, status=SearchTermStatus.NOT_FOUND
    )

    return {
        "total_users": total_users,
        "total_vehicles": total_vehicles,
        "total_reports": total_reports,
        "total_search_terms": {
            "success": success_total_search_terms,
            "not_found": not_found_total_search_terms,
        },
    }


@router.get("/users", description="List users")
async def list_users(
    user: AdminUserDependency,
    request: Request,
    admin_dashboard_service: AdminDashboardServiceDependency,
    params: PaginationParams,
    from_date: datetime | None = Query(
        None, description="Filter from this datetime (inclusive, timezone-aware)"
    ),
    to_date: datetime | None = Query(
        None, description="Filter to this datetime (inclusive, timezone-aware)"
    ),
) -> PaginatedResponse[UserWithCountsSchema]:
    users = await admin_dashboard_service.list_users(
        offset=params.offset, limit=params.limit, from_date=from_date, to_date=to_date
    )
    return paginated_response(
        result=users, request=request, schema=UserWithCountsSchema
    )


@router.get("/vehicles", description="List vehicles")
async def list_vehicles(
    user: AdminUserDependency,
    request: Request,
    admin_dashboard_service: AdminDashboardServiceDependency,
    params: PaginationParams,
    user_id: str | None = None,
    from_date: datetime | None = Query(
        None, description="Filter from this datetime (inclusive, timezone-aware)"
    ),
    to_date: datetime | None = Query(
        None, description="Filter to this datetime (inclusive, timezone-aware)"
    ),
) -> PaginatedResponse[VehicleWithCountsSchema]:
    vehicles = await admin_dashboard_service.list_vehicles(
        user_id=user_id,
        offset=params.offset,
        limit=params.limit,
        from_date=from_date,
        to_date=to_date,
    )
    return paginated_response(
        result=vehicles, request=request, schema=VehicleWithCountsSchema
    )


@router.get("/reports", description="List reports")
async def list_reports(
    user: AdminUserDependency,
    request: Request,
    admin_dashboard_service: AdminDashboardServiceDependency,
    params: PaginationParams,
    vehicle_id: str | None = None,
    user_id: str | None = None,
    from_date: datetime | None = Query(
        None, description="Filter from this datetime (inclusive, timezone-aware)"
    ),
    to_date: datetime | None = Query(
        None, description="Filter to this datetime (inclusive, timezone-aware)"
    ),
) -> PaginatedResponse[VehicleReportSchema]:
    reports = await admin_dashboard_service.list_reports(
        vehicle_id=vehicle_id,
        user_id=user_id,
        offset=params.offset,
        limit=params.limit,
        from_date=from_date,
        to_date=to_date,
    )
    return paginated_response(
        result=reports, request=request, schema=VehicleReportSchema
    )


@router.get("/search-logs", description="List vehicle search logs")
async def list_search_logs(
    user: AdminUserDependency,
    request: Request,
    admin_dashboard_service: AdminDashboardServiceDependency,
    params: PaginationParams,
    status: SearchTermStatus | None = Query(None, description="Filter by status"),
    user_id: UUID | None = Query(None, description="Filter by user ID"),
    from_date: datetime | None = Query(
        None, description="Filter from this datetime (inclusive, timezone-aware)"
    ),
    to_date: datetime | None = Query(
        None, description="Filter to this datetime (inclusive, timezone-aware)"
    ),
) -> PaginatedResponse[VehicleSearchLogResponse]:
    search_logs = await admin_dashboard_service.get_search_logs(
        status=status,
        user_id=user_id,
        limit=params.limit,
        offset=params.offset,
        from_date=from_date,
        to_date=to_date,
    )
    return paginated_response(
        result=search_logs, request=request, schema=VehicleSearchLogResponse
    )
