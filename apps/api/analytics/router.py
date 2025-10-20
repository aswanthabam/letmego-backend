# apps/api/analytics/router.py

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Request, Query

from apps.api.user.models import User
from apps.api.auth.dependency import AdminUserDependency
from avcfastapi.core.authentication.firebase.dependency import FirebaseAuthDependency
from apps.api.analytics.service import AnalyticsServiceDependency
from apps.api.analytics.schema import (
    CTAEventCreate,
    CTAEventResponse,
    CTAAnalyticsResponse,
)
from avcfastapi.core.fastapi.response.models import MessageResponse
from avcfastapi.core.fastapi.response.pagination import (
    PaginatedResponse,
    PaginationParams,
    paginated_response,
)
from avcfastapi.core.database.sqlalchamey.core import SessionDep
from sqlalchemy import select

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


async def get_optional_user(
    session: SessionDep,
    decoded_token: Optional[FirebaseAuthDependency] = None,
) -> Optional[User]:
    """Get current user if authenticated, None otherwise."""
    if not decoded_token:
        return None

    user = await session.scalar(select(User).where(User.uid == decoded_token.uid))
    return user


@router.post("/cta/track", description="Track a call-to-action event")
async def track_cta_event(
    request: Request,
    session: SessionDep,
    analytics_service: AnalyticsServiceDependency,
    event_data: CTAEventCreate,
    decoded_token: Optional[FirebaseAuthDependency] = None,
) -> CTAEventResponse:
    """
    Track a call-to-action button click or event.
    Can be called by authenticated or anonymous users.
    """
    # Extract IP and user agent from request
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Get user if authenticated
    user = await get_optional_user(session, decoded_token)
    user_id = user.id if user else None

    event = await analytics_service.track_cta_event(
        event_data=event_data,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return CTAEventResponse.model_validate(event)


@router.get("/cta/summary", description="Get CTA analytics summary (Admin only)")
async def get_cta_analytics(
    admin: AdminUserDependency,
    analytics_service: AnalyticsServiceDependency,
    start_date: Optional[datetime] = Query(
        None, description="Filter from this date (ISO format)"
    ),
    end_date: Optional[datetime] = Query(
        None, description="Filter until this date (ISO format)"
    ),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    related_entity_type: Optional[str] = Query(
        None, description="Filter by entity type"
    ),
) -> CTAAnalyticsResponse:
    """
    Get aggregated CTA analytics with optional time period and other filters.
    Only accessible by admin users.
    """
    analytics = await analytics_service.get_cta_analytics(
        start_date=start_date,
        end_date=end_date,
        event_type=event_type,
        related_entity_type=related_entity_type,
    )
    return CTAAnalyticsResponse(**analytics)


@router.get("/cta/events", description="Get detailed CTA events (Admin only)")
async def get_cta_events(
    admin: AdminUserDependency,
    analytics_service: AnalyticsServiceDependency,
    pagination: PaginationParams,
    start_date: Optional[datetime] = Query(None, description="Filter from this date"),
    end_date: Optional[datetime] = Query(None, description="Filter until this date"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
) -> PaginatedResponse[CTAEventResponse]:
    """
    Get paginated list of CTA events with optional filters.
    Only accessible by admin users.
    """
    events, total = await analytics_service.get_cta_events(
        skip=pagination.offset,
        limit=pagination.limit,
        start_date=start_date,
        end_date=end_date,
        event_type=event_type,
    )
    return paginated_response(
        result=[CTAEventResponse.model_validate(event) for event in events],
        request=pagination.request,
        schema=CTAEventResponse,
    )
