import traceback
from typing import List, Optional
from uuid import UUID
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload
from typing import Annotated

from apps.api.device.schema import DeviceStatus
from apps.api.device.service import DeviceServiceDependency
from apps.api.notification.schema import NotificationCategory
from apps.api.notification.service import NotificationServiceDependency
from apps.api.user.schema import PrivacyPreference
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
from avcfastapi.core.database.sqlalchamey.core import SessionDep
from avcfastapi.core.exception.authentication import ForbiddenException
from avcfastapi.core.exception.database import NotFoundException
from avcfastapi.core.fastapi.dependency.service_dependency import AbstractService
from avcfastapi.core.storage.sqlalchemy.inputs.file import InputFile
from avcfastapi.core.utils.validations.uuid import is_valid_uuid


class ReportService(AbstractService):
    DEPENDENCIES = {
        "session": SessionDep,
        "notification_service": NotificationServiceDependency,
        "device_service": DeviceServiceDependency,
    }

    def __init__(
        self,
        session: SessionDep,
        notification_service: NotificationServiceDependency,
        device_service: DeviceServiceDependency,
        **kwargs,
    ):
        super().__init__(session=session, **kwargs)
        self.session = session
        self.notification_service = notification_service
        self.device_service = device_service

    async def get_vehicle_by_vehicle_number(self, vehicle_number: str) -> Vehicle:
        """
        Fetches a vehicle by its vehicle number.
        """
        query = select(Vehicle).where(Vehicle.vehicle_number == vehicle_number)
        result = await self.session.execute(query)
        vehicle = result.scalars().first()
        if not vehicle:
            raise NotFoundException(f"Vehicle with number {vehicle_number} not found.")
        return vehicle

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
        vehicle_id: UUID | str,
        user: User,
        notes: Optional[str],
        images: List[UploadFile],
        is_anonymous: bool = False,
        latitude: Optional[str] = None,
        longitude: Optional[str] = None,
        location: Optional[str] = None,
    ) -> VehicleReport:
        if is_valid_uuid(vehicle_id):
            vehicle = await self.get_vehicle(vehicle_id=vehicle_id)
        else:
            vehicle = await self.get_vehicle_by_vehicle_number(vehicle_id)

        if vehicle.user_id == user.id:
            raise ForbiddenException("You cannot report your own vehicle.")

        new_report = VehicleReport(
            vehicle_id=vehicle.id,
            user_id=user.id,
            notes=notes,
            current_status=ReportStatusEnum.ACTIVE.value,
            is_anonymous=is_anonymous,
            latitude=latitude,
            longitude=longitude,
            location=location,
        )
        self.session.add(new_report)
        await self.session.flush()

        primary_image = None
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
                if not primary_image:
                    primary_image = image_obj
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
        if primary_image:
            await self.session.refresh(primary_image)

        if (
            user.privacy_preference == PrivacyPreference.ANONYMOUS.value
            or new_report.is_anonymous
        ):
            user_name = "Anonymous"
        else:
            user_name = user.fullname or "Unkown User"
        notification_title = (
            f"{user_name} reported your vehicle {vehicle.vehicle_number}"
        )

        if notes:
            notification_body = f"{user_name}: {notes[:200]}"
        else:
            notification_body = "Please check the report for details."
        try:
            notification = await self.notification_service.create_notification(
                user_id=vehicle.user_id,
                title=notification_title,
                body=notification_body,
                notification_type=NotificationCategory.PUSH.value,
                image=primary_image.image.get("large") if primary_image else None,
                data={"type": "vehicle_report", "report_id": str(new_report.id)},
            )
            if notification:
                devices = await self.device_service.get_devices(
                    user_id=vehicle.user_id, status=DeviceStatus.ACTIVE, limit=3
                )
                for device in devices:
                    result = await self.notification_service.send_fcm_notification(
                        notification_id=notification.id, device_id=device.id
                    )
                    print(f"Notification sent to device {device.id}: {result}")
        except Exception as e:
            print(f"Failed to create notification: {e}")
            traceback.print_exc()

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
