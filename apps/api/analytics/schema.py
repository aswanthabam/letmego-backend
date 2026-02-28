# apps/api/analytics/schema.py

from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import Field

from avcfastapi.core.fastapi.response.models import CustomBaseModel


class CTAEventCreate(CustomBaseModel):
    """Schema for creating a CTA event"""
    event_type: str = Field(..., min_length=1, max_length=100, description="Type of CTA event")
    event_context: Optional[str] = Field(None, max_length=200, description="Context of the event")
    related_entity_id: Optional[UUID] = Field(None, description="ID of related entity")
    related_entity_type: Optional[str] = Field(None, max_length=50, description="Type of related entity")
    event_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class CTAEventResponse(CustomBaseModel):
    """Schema for CTA event response"""
    id: UUID
    user_id: Optional[UUID]
    event_type: str
    event_context: Optional[str]
    related_entity_id: Optional[UUID]
    related_entity_type: Optional[str]
    event_metadata: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class CTAAnalytics(CustomBaseModel):
    """Schema for CTA analytics response"""
    event_type: str
    count: int
    unique_users: int


class CTAAnalyticsResponse(CustomBaseModel):
    """Schema for aggregated CTA analytics"""
    total_events: int
    analytics_by_type: list[CTAAnalytics]
    date_range: Dict[str, Optional[datetime]]


# ===== B2B SaaS Dashboard Analytics =====

class TimeseriesDataPoint(CustomBaseModel):
    date: str
    amount: float


class RevenueAnalyticsResponse(CustomBaseModel):
    total_calculated: float
    total_collected: float
    total_leakage: float
    leakage_percentage: float
    timeseries: list[TimeseriesDataPoint]


class OccupancyAnalyticsResponse(CustomBaseModel):
    total_sessions: int
    active_sessions: int
    average_duration_hours: float
    vehicle_type_breakdown: Dict[str, int]


class AnalyticsDashboardResponse(CustomBaseModel):
    organization_id: UUID
    organization_name: str
    date_range: Dict[str, datetime]
    revenue: RevenueAnalyticsResponse
    occupancy: OccupancyAnalyticsResponse
