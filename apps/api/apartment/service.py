# apps/api/apartment/service.py

from sqlalchemy import select, and_
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from typing import Annotated, Optional, List
from uuid import UUID

from apps.api.apartment.models import Apartment, ApartmentPermittedVehicle
from apps.api.apartment.schema import (
    ApartmentCreate,
    ApartmentUpdate,
    PermittedVehicleCreate,
    PermittedVehicleUpdate,
)
from apps.api.vehicle.models import Vehicle
from avcfastapi.core.database.sqlalchamey.core import SessionDep
from avcfastapi.core.exception.authentication import ForbiddenException
from avcfastapi.core.exception.request import InvalidRequestException
from avcfastapi.core.fastapi.dependency.service_dependency import AbstractService


class ApartmentService(AbstractService):
    DEPENDENCIES = {"session": SessionDep}

    def __init__(self, session: SessionDep, **kwargs):
        super().__init__(session=session, **kwargs)
        self.session = session

    # ===== Apartment Management =====

    async def create_apartment(self, apartment_data: ApartmentCreate) -> Apartment:
        """
        Create a new apartment (Super admin only).
        """
        apartment = Apartment(**apartment_data.model_dump())
        self.session.add(apartment)
        await self.session.commit()
        await self.session.refresh(apartment)
        return apartment

    async def get_apartment(self, apartment_id: UUID) -> Optional[Apartment]:
        """Get an apartment by ID."""
        result = await self.session.execute(
            select(Apartment)
            .options(joinedload(Apartment.admin))
            .where(Apartment.id == apartment_id, Apartment.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_apartments_by_admin(self, admin_id: UUID) -> List[Apartment]:
        """Get all apartments managed by a specific admin."""
        result = await self.session.execute(
            select(Apartment).where(
                Apartment.admin_id == admin_id, Apartment.deleted_at.is_(None)
            )
        )
        return list(result.scalars().all())

    async def get_all_apartments(
        self, skip: int = 0, limit: int = 100
    ) -> tuple[List[Apartment], int]:
        """Get all apartments with pagination."""
        query = select(Apartment).where(Apartment.deleted_at.is_(None))

        # Get total count
        count_result = await self.session.execute(
            select(sa.func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        # Get paginated results
        query = query.offset(skip).limit(limit).order_by(Apartment.created_at.desc())
        result = await self.session.execute(query)
        apartments = result.scalars().all()

        return list(apartments), total

    async def update_apartment(
        self, apartment_id: UUID, apartment_data: ApartmentUpdate
    ) -> Apartment:
        """Update an apartment."""
        apartment = await self.get_apartment(apartment_id)
        if not apartment:
            raise InvalidRequestException(
                "Apartment not found",
                error_code="APARTMENT_NOT_FOUND",
            )

        update_data = apartment_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(apartment, field, value)

        await self.session.commit()
        await self.session.refresh(apartment)
        return apartment

    async def delete_apartment(self, apartment_id: UUID) -> bool:
        """Soft delete an apartment."""
        apartment = await self.get_apartment(apartment_id)
        if not apartment:
            raise InvalidRequestException(
                "Apartment not found",
                error_code="APARTMENT_NOT_FOUND",
            )

        apartment.soft_delete()
        await self.session.commit()
        return True

    def verify_apartment_admin(self, apartment: Apartment, user_id: UUID):
        """Verify that the user is the admin of the apartment."""
        if apartment.admin_id != user_id:
            raise ForbiddenException(
                "You are not authorized to manage this apartment",
                error_code="NOT_APARTMENT_ADMIN",
            )

    # ===== Permitted Vehicle Management =====

    async def add_permitted_vehicle(
        self,
        apartment_id: UUID,
        vehicle_data: PermittedVehicleCreate,
        admin_id: UUID,
    ) -> ApartmentPermittedVehicle:
        """
        Add a vehicle to the apartment's permitted parking list.
        """
        # Verify apartment exists and user is admin
        apartment = await self.get_apartment(apartment_id)
        if not apartment:
            raise InvalidRequestException(
                "Apartment not found",
                error_code="APARTMENT_NOT_FOUND",
            )

        self.verify_apartment_admin(apartment, admin_id)

        # Verify vehicle exists
        vehicle_result = await self.session.execute(
            select(Vehicle).where(Vehicle.id == vehicle_data.vehicle_id)
        )
        vehicle = vehicle_result.scalar_one_or_none()
        if not vehicle:
            raise InvalidRequestException(
                "Vehicle not found",
                error_code="VEHICLE_NOT_FOUND",
            )

        try:
            permitted_vehicle = ApartmentPermittedVehicle(
                apartment_id=apartment_id,
                vehicle_id=vehicle_data.vehicle_id,
                notes=vehicle_data.notes,
                parking_spot=vehicle_data.parking_spot,
            )
            self.session.add(permitted_vehicle)
            await self.session.commit()
            await self.session.refresh(permitted_vehicle)
            return permitted_vehicle
        except IntegrityError:
            await self.session.rollback()
            raise InvalidRequestException(
                "Vehicle is already permitted in this apartment",
                error_code="VEHICLE_ALREADY_PERMITTED",
            )

    async def remove_permitted_vehicle(
        self,
        apartment_id: UUID,
        vehicle_id: UUID,
        admin_id: UUID,
    ) -> bool:
        """
        Remove a vehicle from the apartment's permitted parking list.
        """
        # Verify apartment exists and user is admin
        apartment = await self.get_apartment(apartment_id)
        if not apartment:
            raise InvalidRequestException(
                "Apartment not found",
                error_code="APARTMENT_NOT_FOUND",
            )

        self.verify_apartment_admin(apartment, admin_id)

        # Find and delete the permitted vehicle record
        result = await self.session.execute(
            select(ApartmentPermittedVehicle).where(
                and_(
                    ApartmentPermittedVehicle.apartment_id == apartment_id,
                    ApartmentPermittedVehicle.vehicle_id == vehicle_id,
                    ApartmentPermittedVehicle.deleted_at.is_(None),
                )
            )
        )
        permitted_vehicle = result.scalar_one_or_none()

        if not permitted_vehicle:
            raise InvalidRequestException(
                "Vehicle permission record not found",
                error_code="PERMISSION_NOT_FOUND",
            )

        await permitted_vehicle.delete(self.session)
        await self.session.commit()
        return True

    async def check_vehicle_permission(
        self,
        apartment_id: UUID,
        vehicle_id: UUID,
        admin_id: UUID,
    ) -> Optional[ApartmentPermittedVehicle]:
        """
        Check if a vehicle is permitted in the apartment's parking.
        """
        # Verify apartment exists and user is admin
        apartment = await self.get_apartment(apartment_id)
        if not apartment:
            raise InvalidRequestException(
                "Apartment not found",
                error_code="APARTMENT_NOT_FOUND",
            )

        self.verify_apartment_admin(apartment, admin_id)

        result = await self.session.execute(
            select(ApartmentPermittedVehicle)
            .options(joinedload(ApartmentPermittedVehicle.apartment))
            .where(
                and_(
                    ApartmentPermittedVehicle.apartment_id == apartment_id,
                    ApartmentPermittedVehicle.vehicle_id == vehicle_id,
                    ApartmentPermittedVehicle.deleted_at.is_(None),
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_permitted_vehicles(
        self,
        apartment_id: UUID,
        admin_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[ApartmentPermittedVehicle], int]:
        """
        Get all permitted vehicles for an apartment.
        """
        # Verify apartment exists and user is admin
        apartment = await self.get_apartment(apartment_id)
        if not apartment:
            raise InvalidRequestException(
                "Apartment not found",
                error_code="APARTMENT_NOT_FOUND",
            )

        self.verify_apartment_admin(apartment, admin_id)

        query = select(ApartmentPermittedVehicle).where(
            and_(
                ApartmentPermittedVehicle.apartment_id == apartment_id,
                ApartmentPermittedVehicle.deleted_at.is_(None),
            )
        )

        # Get total count
        count_result = await self.session.execute(
            select(sa.func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        # Get paginated results
        query = (
            query.options(joinedload(ApartmentPermittedVehicle.vehicle))
            .offset(skip)
            .limit(limit)
            .order_by(ApartmentPermittedVehicle.created_at.desc())
        )
        result = await self.session.execute(query)
        vehicles = result.scalars().all()

        return list(vehicles), total


ApartmentServiceDependency = Annotated[
    ApartmentService, ApartmentService.get_dependency()
]
