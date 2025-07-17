from typing import List, Optional
from uuid import UUID
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload
from typing import Annotated

from core.architecture.service import AbstractService
from core.db.core import SessionDep
from core.exceptions.authentication import ForbiddenException
from core.exceptions.database import NotFoundException
from core.storage.sqlalchemy.inputs.file import InputFile
from apps.api.user.models import User
from apps.api.vehicle.models import Vehicle
from apps.api.vehicle.report.models import (
    VehicleReport,
    VehicleReportImage,
    VehicleReportStatusLog,
)
from apps.api.vehicle.report.schema import (
    ReportStatusEnum,
)


class ReportService(AbstractService):
    DEPENDENCIES = {"session": SessionDep}

    def __init__(self, session: SessionDep, **kwargs):
        super().__init__(session=session, **kwargs)
        self.session = session

    async def get_vehicle(self, vehicle_id: UUID) -> Vehicle:
        """
        Fetches a vehicle by its ID.
        Args:
            session: The SQLAlchemy AsyncSession.
            vehicle_id: The UUID of the vehicle to fetch.
        Returns:
            The Vehicle object if found.
        Raises:
            NotFoundException: If the vehicle does not exist.
        """
        stmt = select(Vehicle).where(Vehicle.id == vehicle_id)
        result = await self.session.execute(stmt)
        vehicle = result.scalars().first()

        if not vehicle:
            raise NotFoundException(f"Vehicle not found.")

        return vehicle

    async def get_report(self, report_id: UUID) -> VehicleReport:
        """
        Fetches a vehicle report by its ID.
        Args:
            session: The SQLAlchemy AsyncSession.
            report_id: The UUID of the report to fetch.
        Returns:
            The VehicleReport object if found.
        Raises:
            NotFoundException: If the report does not exist.
        """
        stmt = select(VehicleReport).where(VehicleReport.id == report_id)
        result = await self.session.execute(stmt)
        report = result.scalars().first()

        if not report:
            raise NotFoundException(f"Vehicle report with ID {report_id} not found.")

        return report

    async def report_vehicle(
        self,
        vehicle_id: UUID,
        user: User,
        notes: Optional[str],
        images: List[UploadFile],
        is_anonymous: bool = False,
    ) -> VehicleReport:
        vehicle = await self.get_vehicle(vehicle_id)

        if vehicle.user_id == user.id:
            raise ForbiddenException("You cannot report your own vehicle.")

        new_report = VehicleReport(
            vehicle_id=vehicle_id,
            user_id=user.id,
            notes=notes,
            current_status=ReportStatusEnum.ACTIVE.value,
            is_anonymous=is_anonymous,
        )
        self.session.add(new_report)
        await self.session.flush()

        # Add images if provided
        if images:
            for image in images:
                image_obj = VehicleReportImage(
                    report_id=new_report.id,
                )
                image_obj.image = InputFile(
                    await image.read(),
                    filename=image.filename,
                    prefix_date=True,
                    unique_filename=True,
                )
                self.session.add(image_obj)
            await self.session.flush()

        # Log initial status
        initial_log = VehicleReportStatusLog(
            report_id=new_report.id,
            user_id=user.id,
            status=ReportStatusEnum.ACTIVE.value,
            notes="Report created and is active.",
        )
        self.session.add(initial_log)

        await self.session.commit()
        await self.session.refresh(new_report)
        return new_report

    async def get_reports(
        self,
        reported_user_id: UUID | None = None,
        user_id: UUID | None = None,
        is_closed: bool | None = None,
        current_status: Optional[ReportStatusEnum] = "active",
        limit: int = 10,
        offset: int = 0,
    ) -> List[VehicleReport]:
        """
        Retrieves all vehicle reports.
        """
        if not reported_user_id and not user_id:
            raise ValueError(
                "Either reported_user_id or user_id must be provided to filter reports."
            )
        query = (
            select(VehicleReport)
            .join(Vehicle, VehicleReport.vehicle_id == Vehicle.id)
            .options(selectinload(VehicleReport.images))
            .options(joinedload(VehicleReport.vehicle))
            .options(joinedload(VehicleReport.reporter))
            .order_by(VehicleReport.created_at.desc())
        )
        if reported_user_id:
            query = query.where(VehicleReport.user_id == reported_user_id)
        if user_id:
            query = query.where(Vehicle.user_id == user_id)
        if current_status:
            query = query.where(VehicleReport.current_status == current_status.value)
        if is_closed is not None:
            query = query.where(VehicleReport.is_closed == is_closed)

        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        result = await self.session.execute(query)
        reports = result.scalars().unique().all()
        return reports

    async def update_report_status(
        self,
        report_id: UUID,
        new_status: ReportStatusEnum,
        user_id: UUID,
        notes: Optional[str] = None,
    ) -> VehicleReport:
        report = await self.get_report(report_id=report_id)
        allowed_statuses = []

        if report.user_id == user_id:
            allowed_statuses = [
                ReportStatusEnum.REPORTER_CLOSED,
                ReportStatusEnum.REPORTER_RESOLVED,
                ReportStatusEnum.REPORTER_REJECTED,
            ]

        await self.session.refresh(report, ["vehicle"])

        if report.vehicle.user_id == user_id:
            allowed_statuses = [
                ReportStatusEnum.OWNER_RESOLVED,
                ReportStatusEnum.OWNER_REJECTED,
                ReportStatusEnum.OWNER_SEEN,
                ReportStatusEnum.OWNER_RESPONDED,
                ReportStatusEnum.OWNER_NOTIFIED,
            ]

        if new_status not in allowed_statuses:
            raise ForbiddenException(
                "You do not have permission to update the status of this report."
            )

        report.current_status = new_status
        report.is_closed = new_status.is_closed

        status_log = VehicleReportStatusLog(
            report_id=report.id,
            user_id=user_id,
            status=new_status.value,
            notes=notes,
        )
        self.session.add(status_log)

        await self.session.commit()
        await self.session.refresh(report)
        return report

    async def get_report_details(
        self, report_id: UUID, current_user_id: UUID
    ) -> VehicleReport:
        """
        Retrieves a specific vehicle report with its current status and log.
        A user can see a report if they are the reporter or the owner of the reported vehicle.
        Args:
            sessionn: The SQLAlchemy AsyncSession.
            report_id: The UUID of the report to retrieve.
            current_user_id: The UUID of the user requesting the report.
        Returns:
            The VehicleReport object with images and status logs.
        Raises:
            NotFoundException: If the report does not exist.
            PermissionDeniedException: If the user is not authorized to view this report.
        """
        stmt = (
            select(VehicleReport)
            .where(VehicleReport.id == report_id)
            .options(selectinload(VehicleReport.images))
            .options(selectinload(VehicleReport.status_logs))
            .options(joinedload(VehicleReport.vehicle).joinedload(Vehicle.owner))
            .options(joinedload(VehicleReport.reporter))
        )
        result = await self.session.execute(stmt)
        report = result.scalars().first()

        if not report:
            raise NotFoundException(f"Vehicle report with ID {report_id} not found.")

        # Permission check: Current user must be either the reporter or the reported vehicle owner
        is_reporter = (
            report.user_id == current_user_id
        )  # `user_id` on report is the reporter
        is_reported_vehicle_owner = False
        if (
            report.vehicle
            and hasattr(report.vehicle, "user_id")
            and report.vehicle.user_id == current_user_id
        ):
            is_reported_vehicle_owner = True

        if not (is_reporter or is_reported_vehicle_owner):
            raise ForbiddenException("You do not have permission to view this report.")

        return report


ReportServiceDependency = Annotated[ReportService, ReportService.get_dependency()]
