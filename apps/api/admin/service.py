from typing import Annotated, List, Optional
from datetime import datetime
import uuid
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload, joinedload

from apps.api.user.models import User
from apps.api.vehicle.models import SearchTermStatus, Vehicle, VehicleSearchLog
from apps.api.vehicle.report.models import VehicleReport
from avcfastapi.core.database.sqlalchamey.core import SessionDep
from avcfastapi.core.fastapi.dependency.service_dependency import AbstractService


class AdminDashboardService(AbstractService):
    DEPENDENCIES = {"session": SessionDep}

    def __init__(self, session: SessionDep, **kwargs):
        super().__init__(**kwargs)
        self.session = session

    # --- Utility filter ---
    def _date_filter(
        self, column, from_date: datetime | None, to_date: datetime | None
    ):
        conds = []
        if from_date:
            conds.append(column >= from_date)
        if to_date:
            conds.append(column <= to_date)
        return and_(*conds) if conds else None

    # --- Counts ---
    async def get_users_count(
        self, from_date: datetime | None = None, to_date: datetime | None = None
    ) -> int:
        query = select(func.count(User.id))
        date_cond = self._date_filter(User.created_at, from_date, to_date)
        if date_cond is not None:
            query = query.where(date_cond)
        result = await self.session.execute(query)
        return result.scalar_one()

    async def get_vehicles_count(
        self, from_date: datetime | None = None, to_date: datetime | None = None
    ) -> int:
        query = select(func.count(Vehicle.id))
        date_cond = self._date_filter(Vehicle.created_at, from_date, to_date)
        if date_cond is not None:
            query = query.where(date_cond)
        result = await self.session.execute(query)
        return result.scalar_one()

    async def get_reports_count(
        self, from_date: datetime | None = None, to_date: datetime | None = None
    ) -> int:
        query = select(func.count(VehicleReport.id))
        date_cond = self._date_filter(VehicleReport.created_at, from_date, to_date)
        if date_cond is not None:
            query = query.where(date_cond)
        result = await self.session.execute(query)
        return result.scalar_one()

    # --- Lists ---
    async def list_users(
        self,
        offset: int = 0,
        limit: int = 10,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ):
        # Subquery for vehicle counts
        vehicle_count_subq = (
            select(Vehicle.user_id, func.count(Vehicle.id).label("vehicle_count"))
            .group_by(Vehicle.user_id)
            .subquery()
        )

        # Subquery for report counts per user
        report_query = (
            select(
                User.id.label("user_id"),
                func.count(VehicleReport.id).label("report_count"),
            )
            .join(Vehicle, Vehicle.id == VehicleReport.vehicle_id)
            .join(User, User.id == Vehicle.user_id)
            .group_by(User.id)
        )
        date_cond = self._date_filter(VehicleReport.created_at, from_date, to_date)
        if date_cond is not None:
            report_query = report_query.where(date_cond)

        report_count_subq = report_query.subquery()

        query = (
            select(
                User,
                vehicle_count_subq.c.vehicle_count,
                report_count_subq.c.report_count,
            )
            .outerjoin(vehicle_count_subq, User.id == vehicle_count_subq.c.user_id)
            .outerjoin(report_count_subq, User.id == report_count_subq.c.user_id)
            .offset(offset)
            .limit(limit)
            .order_by(User.created_at.desc())
        )

        # Apply date filter for user listing itself
        user_date_cond = self._date_filter(User.created_at, from_date, to_date)
        if user_date_cond is not None:
            query = query.where(user_date_cond)

        result = await self.session.execute(query)
        rows = result.all()

        return [
            {
                "user": row[0],
                "total_vehicle_count": row[1] or 0,
                "total_reports_against_user": row[2] or 0,
            }
            for row in rows
        ]

    async def list_vehicles(
        self,
        user_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 10,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ):
        # Subquery for report counts per vehicle
        report_query = select(
            VehicleReport.vehicle_id,
            func.count(VehicleReport.id).label("report_count"),
        ).group_by(VehicleReport.vehicle_id)
        date_cond = self._date_filter(VehicleReport.created_at, from_date, to_date)
        if date_cond is not None:
            report_query = report_query.where(date_cond)

        report_count_subq = report_query.subquery()

        query = (
            select(Vehicle, report_count_subq.c.report_count)
            .outerjoin(report_count_subq, Vehicle.id == report_count_subq.c.vehicle_id)
            .options(joinedload(Vehicle.owner))
        ).order_by(Vehicle.created_at.desc())

        if user_id is not None:
            query = query.where(Vehicle.user_id == user_id)

        # Apply date filter for vehicle itself
        vehicle_date_cond = self._date_filter(Vehicle.created_at, from_date, to_date)
        if vehicle_date_cond is not None:
            query = query.where(vehicle_date_cond)

        query = query.offset(offset).limit(limit)

        result = await self.session.execute(query)
        rows = result.all()

        return [
            {
                "vehicle": row[0],
                "total_reports_against_user": row[1] or 0,
            }
            for row in rows
        ]

    async def list_reports(
        self,
        vehicle_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 10,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ):
        query = (
            select(VehicleReport)
            .join(Vehicle, Vehicle.id == VehicleReport.vehicle_id)
            .options(
                selectinload(VehicleReport.images),
                joinedload(VehicleReport.reporter),
                joinedload(VehicleReport.vehicle).joinedload(Vehicle.owner),
            )
        ).order_by(VehicleReport.created_at.desc())

        if vehicle_id is not None:
            query = query.where(VehicleReport.vehicle_id == vehicle_id)

        if user_id is not None:
            query = query.where(Vehicle.user_id == user_id)

        # Apply date filter
        report_date_cond = self._date_filter(
            VehicleReport.created_at, from_date, to_date
        )
        if report_date_cond is not None:
            query = query.where(report_date_cond)

        query = query.offset(offset).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_search_logs(
        self,
        status: Optional[SearchTermStatus] = None,
        user_id: Optional[uuid.UUID] = None,
        limit: Optional[int] = 10,
        offset: int = 0,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[VehicleSearchLog]:
        query = select(VehicleSearchLog).options(joinedload(VehicleSearchLog.user))

        date_cond = self._date_filter(VehicleSearchLog.created_at, from_date, to_date)
        if date_cond is not None:
            query = query.where(date_cond)

        if status:
            query = query.where(VehicleSearchLog.status == status.value)

        if user_id:
            query = query.where(VehicleSearchLog.user_id == user_id)

        if offset and offset > 0:
            query = query.offset(offset)

        if limit and limit > 0:
            query = query.limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def count_search_logs(
        self,
        status: Optional[SearchTermStatus] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> int:
        query = select(func.count(VehicleSearchLog.id))

        date_cond = self._date_filter(VehicleSearchLog.created_at, from_date, to_date)
        if date_cond is not None:
            query = query.where(date_cond)

        if status:
            query = query.where(VehicleSearchLog.status == status.value)

        result = await self.session.execute(query)
        return result.scalar_one()


AdminDashboardServiceDependency = Annotated[
    AdminDashboardService, AdminDashboardService.get_dependency()
]
