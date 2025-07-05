from typing import List, Optional
from uuid import UUID
from fastapi import (
    APIRouter,
    Request,
    status,
    Query,
    UploadFile,
    File,
    Form,
)

from apps.api.auth.dependency import UserDependency
from apps.api.vehicle.report.service import ReportServiceDependency
from apps.api.vehicle.report.schema import (
    ReportStatusEnum,
    VehicleReportMin,
    VehicleReportDetail,
    VehicleReportMin,
)
from core.response.pagination import (
    PaginatedResponse,
    PaginationParams,
    paginated_response,
)

router = APIRouter(prefix="/report", tags=["Vehicle Reports"])


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Report a vehicle with image uploads",
    description="Allows a user to report a specific vehicle, including multiple image files.",
)
async def report_vehicle_endpoint(
    user: UserDependency,
    report_service: ReportServiceDependency,
    vehicle_id: UUID = Form(..., description="ID of the vehicle being reported."),
    notes: Optional[str] = Form(
        None, description="Optional notes or details about the report."
    ),
    images: List[UploadFile] = File(
        ..., description="Multiple image files to upload for the report."
    ),
) -> VehicleReportDetail:
    report = await report_service.report_vehicle(
        vehicle_id=vehicle_id,
        user=user,
        notes=notes,
        images=images,
    )
    return await report_service.get_report_details(
        report_id=report.id, current_user_id=user.id
    )


@router.get(
    "/list",
    summary="See reports towards my vehicles",
    description="Retrieves a list of vehicle reports where the reported vehicle belongs to the current user.",
)
async def get_reports_towards_me(
    report_service: ReportServiceDependency,
    request: Request,
    user: UserDependency,
    pagination: PaginationParams,
    current_status: Optional[ReportStatusEnum] = Query(
        None,
    ),
) -> PaginatedResponse[VehicleReportMin]:
    """
    Endpoint to view reports targeted at vehicles owned by the authenticated user.
    - Requires `current_user` to be authenticated.
    - Returns a paginated list of reports.
    """
    reports = await report_service.get_reports_for_user(
        current_user_id=user.id,
        current_status=current_status,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return paginated_response(request=request, result=reports, schema=VehicleReportMin)


@router.patch(
    "/status/{report_id}",
    summary="Update report status (by reported person)",
    description="Allows the owner of the reported vehicle to update the report's status.",
)
async def update_report_status(
    user: UserDependency,
    report_id: UUID,
    report_service: ReportServiceDependency,
    new_status: ReportStatusEnum = Form(
        ..., description="New status to set for the report."
    ),
    notes: Optional[str] = Form(
        None, description="Optional notes or comments for the status update."
    ),
) -> VehicleReportDetail:
    """
    Endpoint to update the status of a vehicle report.
    - Requires `current_user` to be the owner of the reported vehicle.
    """
    report = await report_service.update_report_status(
        report_id=report_id,
        new_status=new_status,
        user_id=user.id,
        notes=notes,
    )
    return await report_service.get_report_details(
        report_id=report.id, current_user_id=user.id
    )


@router.get(
    "/detail/{report_id}",
    summary="Get report details",
    description="Retrieves a specific vehicle report with its current status and log history.",
)
async def get_report_details(
    user: UserDependency,
    report_id: UUID,
    report_service: ReportServiceDependency,
) -> VehicleReportDetail:
    """
    Endpoint to retrieve the full details of a specific vehicle report,
    including images and status logs.
    - Requires `current_user` to be either the reporter or the owner of the reported vehicle.
    """
    return await report_service.get_report_details(
        report_id=report_id,
        current_user_id=user.id,
    )
