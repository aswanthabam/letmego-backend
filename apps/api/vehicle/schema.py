# apps/vehicle/schema.py
from datetime import datetime
from enum import Enum
from uuid import UUID
from pydantic import Field, field_validator
import re
from typing import Optional

from apps.api.user.schema import UserPrivacyWrapper
from core.response.models import CustomBaseModel

from enum import Enum

vehicle_type_display_text = {
    "car": "Car",
    "motorcycle": "Motorcycle",
    "truck": "Truck",
    "bus": "Bus",
    "suv": "SUV",
    "pickup_truck": "Pickup Truck",
    "scooter": "Scooter",
    "trailer": "Trailer",
    "rickshaw": "Rickshaw",
    "auto_rickshaw": "Auto Rickshaw",
    "tractor": "Tractor",
    "ambulance": "Ambulance",
    "fire_truck": "Fire Truck",
    "police_vehicle": "Police Vehicle",
    "taxi": "Taxi",
    "other": "Other",
}

fuel_type_display_text = {
    "petrol": "Petrol",
    "diesel": "Diesel",
    "electric": "Electric",
    "hybrid": "Hybrid (Petrol/Electric)",
    "cng": "CNG (Compressed Natural Gas)",
    "lpg": "LPG (Liquefied Petroleum Gas)",
    "hydrogen": "Hydrogen",
    "biofuel": "Biofuel",
    "other": "Other",
}


class FuelType(Enum):
    PETROL = "petrol"
    DIESEL = "diesel"
    ELECTRIC = "electric"
    HYBRID = "hybrid"
    CNG = "cng"
    LPG = "lpg"
    HYDROGEN = "hydrogen"
    BIOFUEL = "biofuel"
    OTHER = "other"

    @property
    def display_text(self) -> str:
        return fuel_type_display_text[self.value]


class VehicleType(Enum):
    CAR = "car"
    MOTORCYCLE = "motorcycle"
    TRUCK = "truck"
    BUS = "bus"
    SUV = "suv"
    PICKUP_TRUCK = "pickup_truck"
    SCOOTER = "scooter"
    TRAILER = "trailer"
    RICKSHAW = "rickshaw"
    AUTO_RICKSHAW = "auto_rickshaw"
    TRACTOR = "tractor"
    AMBULANCE = "ambulance"
    FIRE_TRUCK = "fire_truck"
    POLICE_VEHICLE = "police_vehicle"
    TAXI = "taxi"
    OTHER = "other"

    @property
    def display_text(self) -> str:
        return vehicle_type_display_text[self.value]


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


class VehicleOwnerMin(UserPrivacyWrapper):
    id: UUID = Field(...)
    fullname: str | None = Field(None)
    email: str | None = Field(None)
    phone_number: str | None = Field(None)


class VehicleDetailResponse(CustomBaseModel):
    id: UUID = Field(...)
    name: str | None = Field(None)
    vehicle_number: str = Field(
        ...,
        min_length=1,
        max_length=20,
    )
    owner: VehicleOwnerMin | None = Field(None)
    fuel_type: FuelType | None = Field(None)
    vehicle_type: VehicleType | None = Field(None)
    brand: str | None = Field(None)
    image: dict | None = Field(None)
    is_verified: bool = Field(False)

    @field_validator("vehicle_type", "fuel_type", mode="after")
    def validate_enum_fields(cls, v):
        if v:
            if hasattr(v, "value"):
                return v.display_text
        return v


class VehicleResponseMin(CustomBaseModel):
    id: UUID = Field(...)
    name: str | None = Field(None)
    vehicle_number: str = Field(
        ...,
        min_length=1,
        max_length=20,
    )
    fuel_type: FuelType | None = Field(None)
    vehicle_type: VehicleType | None = Field(None)
    is_verified: bool = Field(False)

    @field_validator("vehicle_type", "fuel_type", mode="after")
    def validate_enum_fields(cls, v):
        if v:
            if hasattr(v, "value"):
                return {
                    "key": v.value,
                    "value": v.display_text,
                }
        return v


class CreateVehicleRequest(CustomBaseModel):
    name: str | None = Field(None)
    vehicle_number: str = Field(
        ...,
        min_length=1,
        max_length=20,
    )
    vehicle_type: VehicleType | None = Field(None)
    fuel_type: FuelType | None = Field(None)
    brand: str | None = Field(None)


class UpdateVehicleRequest(CustomBaseModel):
    name: str | None = Field(None)
    vehicle_number: str = Field(
        ...,
        min_length=1,
        max_length=20,
    )
    vehicle_type: VehicleType | None = Field(None)
    fuel_type: FuelType | None = Field(None)
    brand: str | None = Field(None)


class VehicleTypeResponse(CustomBaseModel):
    """Response model for vehicle type choices"""

    value: str
    display_name: str


class FuelTypeResponse(CustomBaseModel):
    """Response model for fuel type choices"""

    value: str
    display_name: str
