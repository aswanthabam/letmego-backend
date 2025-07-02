from datetime import datetime
from uuid import UUID
from pydantic import Field, field_validator
import re

from core.response.models import CustomBaseModel


class VehicleValidatorMixin:
    @field_validator("vehicle_number")
    def validate_vehicle_number(cls, v):
        v = re.sub(r"[^a-zA-Z0-9]", "", v)
        v = v.strip().upper()

        patterns = [
            # Standard private/commercial format
            r"^[A-Z]{2}[0-9]{1,2}[A-Z]{0,3}[0-9]{4}$",
            # Military (↑24B123456Z)
            r"^↑[0-9]{2}[A-Z][0-9]{6}[A-Z]$",
            # Diplomatic (199 CD 99 / 99 UN 99 / etc.)
            r"^\d{2,3}\s(CD|CC|UN|IOD)\s\d{2,4}$",
            # Temporary (e.g., T0124AN0123A)
            r"^T\d{4}[A-Z]{2}\d{4}[A-Z]$",
            # Trade plates (e.g., AN01C0123TC0123)
            r"^[A-Z]{2}\d{2}[A-Z]?\d{4}TC\d{4}$",
        ]

        if not any(re.fullmatch(p, v) for p in patterns):
            raise ValueError("Invalid Indian vehicle registration number format: " + v)

        return v


class VehicleResponse(CustomBaseModel):
    id: UUID = Field(...)
    name: str | None = Field(None)
    vehicle_number: str = Field(
        ...,
        min_length=1,
        max_length=20,
    )
    is_verified: bool = Field(False)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)


class CreateVehicleRequest(CustomBaseModel):
    name: str | None = Field(None)
    vehicle_number: str = Field(
        ...,
        min_length=1,
        max_length=20,
    )


class UpdateVehicleRequest(CustomBaseModel):
    name: str | None = Field(None)
    vehicle_number: str = Field(
        ...,
        min_length=1,
        max_length=20,
    )
