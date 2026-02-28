# apps/api/analytics/service.py

from sqlalchemy import select, func
import sqlalchemy as sa
from typing import Annotated, Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from apps.api.analytics.models import CallToActionEvent
from apps.api.analytics.schema import CTAEventCreate, CTAAnalytics
from avcfastapi.core.database.sqlalchamey.core import SessionDep
from avcfastapi.core.fastapi.dependency.service_dependency import AbstractService


class AnalyticsService(AbstractService):
    DEPENDENCIES = {"session": SessionDep}

    def __init__(self, session: SessionDep, **kwargs):
        super().__init__(session=session, **kwargs)
        self.session = session

    async def track_cta_event(
        self,
        event_data: CTAEventCreate,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> CallToActionEvent:
        """
        Track a call-to-action event.

        Args:
            event_data: CTAEventCreate schema with event details
            user_id: Optional UUID of the user (if authenticated)
            ip_address: IP address of the requester
            user_agent: User agent string

        Returns:
            CallToActionEvent: Created event instance
        """
        event = CallToActionEvent(
            user_id=user_id,
            event_type=event_data.event_type,
            event_context=event_data.event_context,
            related_entity_id=event_data.related_entity_id,
            related_entity_type=event_data.related_entity_type,
            event_metadata=event_data.event_metadata,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        return event

    async def get_cta_analytics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_type: Optional[str] = None,
        related_entity_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get aggregated CTA analytics with optional filters.

        Args:
            start_date: Filter events from this date
            end_date: Filter events until this date
            event_type: Filter by specific event type
            related_entity_type: Filter by related entity type

        Returns:
            Dictionary containing analytics data
        """
        # Base query
        query = select(CallToActionEvent)

        # Apply filters
        if start_date:
            query = query.where(CallToActionEvent.created_at >= start_date)
        if end_date:
            query = query.where(CallToActionEvent.created_at <= end_date)
        if event_type:
            query = query.where(CallToActionEvent.event_type == event_type)
        if related_entity_type:
            query = query.where(CallToActionEvent.related_entity_type == related_entity_type)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total_events = total_result.scalar_one()

        # Get analytics by event type
        analytics_query = select(
            CallToActionEvent.event_type,
            func.count(CallToActionEvent.id).label("count"),
            func.count(func.distinct(CallToActionEvent.user_id)).label("unique_users"),
        ).group_by(CallToActionEvent.event_type)

        # Apply same filters to analytics query
        if start_date:
            analytics_query = analytics_query.where(CallToActionEvent.created_at >= start_date)
        if end_date:
            analytics_query = analytics_query.where(CallToActionEvent.created_at <= end_date)
        if event_type:
            analytics_query = analytics_query.where(CallToActionEvent.event_type == event_type)
        if related_entity_type:
            analytics_query = analytics_query.where(
                CallToActionEvent.related_entity_type == related_entity_type
            )

        analytics_result = await self.session.execute(analytics_query)
        analytics_rows = analytics_result.all()

        analytics_by_type = [
            CTAAnalytics(
                event_type=row.event_type,
                count=row.count,
                unique_users=row.unique_users,
            )
            for row in analytics_rows
        ]

        return {
            "total_events": total_events,
            "analytics_by_type": analytics_by_type,
            "date_range": {
                "start_date": start_date,
                "end_date": end_date,
            },
        }

    async def get_cta_events(
        self,
        skip: int = 0,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_type: Optional[str] = None,
    ) -> tuple[List[CallToActionEvent], int]:
        """
        Get list of CTA events with optional filters.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            start_date: Filter events from this date
            end_date: Filter events until this date
            event_type: Filter by specific event type

        Returns:
            Tuple of (list of events, total count)
        """
        query = select(CallToActionEvent)

        # Apply filters
        if start_date:
            query = query.where(CallToActionEvent.created_at >= start_date)
        if end_date:
            query = query.where(CallToActionEvent.created_at <= end_date)
        if event_type:
            query = query.where(CallToActionEvent.event_type == event_type)

        # Get total count
        count_result = await self.session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        # Get paginated results
        query = query.offset(skip).limit(limit).order_by(CallToActionEvent.created_at.desc())
        result = await self.session.execute(query)
        events = result.scalars().all()

        return list(events), total
        return list(events), total

    # ===== B2B SaaS Dashboard Analytics =====
    
    async def get_organization_revenue_analytics(
        self,
        organization_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Calculate revenue, collected amounts, and true revenue leakage
        for all slots within an organization over a given time frame.
        """
        from apps.api.parking.models import ParkingSession, PaymentStatus, ParkingSlot
        
        # 1. Join Sessions -> Slots to filter by Organization
        query = (
            select(
                func.sum(ParkingSession.calculated_fee).label("total_calculated"),
                func.sum(
                    sa.case(
                        (ParkingSession.payment_status == PaymentStatus.COMPLETED, ParkingSession.calculated_fee),
                        else_=0
                    )
                ).label("total_collected"),
                func.date(ParkingSession.check_out_time).label("date")
            )
            .join(ParkingSlot, ParkingSession.slot_id == ParkingSlot.id)
            .where(
                ParkingSlot.organization_id == organization_id,
                ParkingSession.check_out_time != None,
                ParkingSession.check_out_time >= start_date,
                ParkingSession.check_out_time <= end_date,
                ParkingSession.deleted_at.is_(None)
            )
            .group_by(func.date(ParkingSession.check_out_time))
            .order_by(func.date(ParkingSession.check_out_time))
        )
        
        result = await self.session.execute(query)
        rows = result.all()
        
        total_calc = 0.0
        total_coll = 0.0
        timeseries = []
        
        for row in rows:
            calc = float(row.total_calculated or 0)
            coll = float(row.total_collected or 0)
            
            total_calc += calc
            total_coll += coll
            
            timeseries.append({
                "date": str(row.date),
                "amount": coll
            })
            
        leakage = total_calc - total_coll
        leakage_pct = (leakage / total_calc * 100) if total_calc > 0 else 0.0
        
        return {
            "total_calculated": total_calc,
            "total_collected": total_coll,
            "total_leakage": leakage,
            "leakage_percentage": round(leakage_pct, 2),
            "timeseries": timeseries
        }
        
    async def get_organization_occupancy_analytics(
        self,
        organization_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Calculate parking yield and utilization metrics for the Dashboard.
        """
        from apps.api.parking.models import ParkingSession, ParkingSlot
        
        # Get total and completed sessions
        base_query = (
            select(ParkingSession)
            .join(ParkingSlot, ParkingSession.slot_id == ParkingSlot.id)
            .where(
                ParkingSlot.organization_id == organization_id,
                ParkingSession.check_in_time >= start_date,
                ParkingSession.check_in_time <= end_date,
                ParkingSession.deleted_at.is_(None)
            )
        )
        
        sessions_result = await self.session.execute(base_query)
        sessions = sessions_result.scalars().all()
        
        total_sessions = len(sessions)
        active_sessions = sum(1 for s in sessions if s.check_out_time is None)
        
        total_duration_seconds = 0
        completed_count = 0
        vehicle_breakdown = {}
        
        for s in sessions:
            # Breakdown by vehicle type
            v_type = s.vehicle_type.value if hasattr(s.vehicle_type, 'value') else str(s.vehicle_type)
            vehicle_breakdown[v_type] = vehicle_breakdown.get(v_type, 0) + 1
            
            # Duration math
            if s.check_out_time:
                duration = (s.check_out_time - s.check_in_time).total_seconds()
                total_duration_seconds += duration
                completed_count += 1
                
        avg_duration_hours = (total_duration_seconds / completed_count / 3600) if completed_count > 0 else 0.0
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "average_duration_hours": round(avg_duration_hours, 2),
            "vehicle_type_breakdown": vehicle_breakdown
        }


AnalyticsServiceDependency = Annotated[AnalyticsService, AnalyticsService.get_dependency()]

