# apps/vehicle/service.py
import re
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from typing import Annotated, Optional, List
from uuid import UUID
from fastapi import UploadFile
from sqlalchemy.orm import joinedload

from apps.api.vehicle.models import Vehicle
from core.architecture.service import AbstractService
from core.db.core import SessionDep
from core.exceptions.authentication import (
    ForbiddenException,
)
from core.exceptions.request import (
    InvalidRequestException,
)
from core.storage.sqlalchemy.inputs.file import (
    InputFile,
)  # Replace with your actual import path


class VehicleService(AbstractService):
    DEPENDENCIES = {"session": SessionDep}

    def __init__(self, session: SessionDep, **kwargs):
        super().__init__(session=session, **kwargs)
        self.session = session

    async def create_vehicle(
        self,
        vehicle_number: str,
        user_id: UUID,
        name: Optional[str] = None,
        vehicle_type: str = None,
        fuel_type: Optional[str] = None,
        brand: Optional[str] = None,
        image: Optional[UploadFile] = None,
        is_verified: bool = False,
    ) -> Vehicle:
        """
        Create a new vehicle record.

        Args:
            session: AsyncSession database connection
            vehicle_number: Unique vehicle number
            user_id: UUID of the vehicle owner
            name: Optional vehicle name
            vehicle_type: Type of vehicle from VehicleType enum
            brand: Vehicle brand
            image: Optional uploaded image file
            is_verified: Vehicle verification status (default: False)

        Returns:
            Vehicle: Created vehicle instance

        Raises:
            IntegrityError: If vehicle_number already exists or user_id is invalid
        """
        try:
            vehicle_number = re.sub(r"[^a-zA-Z0-9]", "", vehicle_number).upper()
            vehicle = Vehicle(
                vehicle_number=vehicle_number,
                name=name,
                vehicle_type=vehicle_type,
                brand=brand,
                user_id=user_id,
                is_verified=is_verified,
                fuel_type=fuel_type,
            )

            # Handle image upload
            if image:
                vehicle.image = InputFile(
                    content=await image.read(),
                    filename=image.filename,
                    unique_filename=True,
                    prefix_date=True,
                )

            self.session.add(vehicle)
            await self.session.commit()
            await self.session.refresh(vehicle)
            return vehicle

        except IntegrityError as e:
            await self.session.rollback()
            raise e

    async def get_vehicle(
        self,
        user_id: UUID = None,
        vehicle_id: Optional[UUID] = None,
        vehicle_number: Optional[str] = None,
        include_deleted: bool = False,
    ) -> Optional[Vehicle]:
        """
        Get a single vehicle by ID.

        Args:
            session: AsyncSession database connection
            user_id: UUID of the vehicle owner
            vehicle_id: UUID of the vehicle
            include_deleted: Whether to include soft-deleted records

        Returns:
            Vehicle or None: Found vehicle instance or None if not found
        """
        query = select(Vehicle).options(joinedload(Vehicle.owner))

        if user_id is not None:
            query = query.where(Vehicle.user_id == user_id)

        if vehicle_number is not None:
            vehicle_number = re.sub(r"[^a-zA-Z0-9]", "", vehicle_number).upper()
            query = query.where(Vehicle.vehicle_number.ilike(vehicle_number))

        if vehicle_id is not None:
            query = query.where(Vehicle.id == vehicle_id)

        if not include_deleted:
            query = query.where(Vehicle.deleted_at.is_(None))

        result = await self.session.execute(query)
        vehicle = result.scalar()

        if not vehicle:
            raise InvalidRequestException("Vehicle not found")

        return vehicle

    async def search_vehicle_number(
        self,
        vehicle_number: str,
        limit: Optional[int] = 10,
        offset: int = 0,
    ) -> List[Vehicle]:
        """
        Search for a vehicle by its number.
        """
        vehicle_number = re.sub(r"[^a-zA-Z0-9]", "", vehicle_number).upper()

        query = select(Vehicle).where(
            Vehicle.vehicle_number.ilike(f"%{vehicle_number}%")
        )
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        results = list(await self.session.scalars(query))
        return results

    async def get_vehicles(
        self,
        user_id: Optional[UUID] = None,
        vehicle_type: str = None,
        fuel_type: Optional[str] = None,
        brand: Optional[str] = None,
        is_verified: Optional[bool] = None,
        search_term: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Vehicle]:
        """
        Get multiple vehicles with optional filtering.

        Args:
            session: AsyncSession database connection
            user_id: Filter by owner user ID
            vehicle_type: Filter by vehicle type
            brand: Filter by brand
            is_verified: Filter by verification status
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List[Vehicle]: List of vehicle instances
        """
        query = select(Vehicle)

        # Apply filters
        if user_id:
            query = query.where(Vehicle.user_id == user_id)

        if vehicle_type:
            query = query.where(Vehicle.vehicle_type == vehicle_type)

        if fuel_type:
            query = query.where(Vehicle.fuel_type == fuel_type)

        if brand:
            query = query.where(Vehicle.brand.ilike(f"%{brand}%"))

        if search_term:
            search_term = f"%{search_term}%"
            query = query.where(
                (Vehicle.vehicle_number.ilike(search_term))
                | (Vehicle.name.ilike(search_term))
                | (Vehicle.brand.ilike(search_term))
            )

        if is_verified is not None:
            query = query.where(Vehicle.is_verified == is_verified)

        # Only include non-deleted records
        query = query.where(Vehicle.deleted_at.is_(None))

        # Apply pagination
        if offset > 0:
            query = query.offset(offset)

        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def update_vehicle(
        self,
        vehicle_id: UUID,
        user_id: UUID,
        vehicle_number: str,
        name: Optional[str] = None,
        vehicle_type: str = None,
        fuel_type: Optional[str] = None,
        brand: Optional[str] = None,
        image: Optional[UploadFile] = None,
    ) -> Optional[Vehicle]:
        """
        Update a vehicle record.

        Args:
            session: AsyncSession database connection
            vehicle_id: UUID of the vehicle to update
            user_id: UUID of the vehicle owner
            vehicle_number: Updated vehicle number
            name: Updated vehicle name
            vehicle_type: Updated vehicle type
            brand: Updated vehicle brand
            image: Optional new image file

        Returns:
            Vehicle or None: Updated vehicle instance or None if not found

        Raises:
            IntegrityError: If update violates constraints (e.g., duplicate vehicle_number)
        """
        try:
            # First check if the vehicle exists and is not soft-deleted
            existing_vehicle = await self.get_vehicle(
                user_id=user_id, vehicle_id=vehicle_id
            )
            if not existing_vehicle:
                return None
            if existing_vehicle.user_id != user_id:
                raise ForbiddenException(
                    "You do not have permission to update this vehicle."
                )

            # Prepare update data
            update_data = {
                "vehicle_number": vehicle_number,
                "name": name,
                "vehicle_type": vehicle_type,
                "fuel_type": fuel_type,
                "brand": brand,
            }

            # Handle image update
            if image:
                update_data["image"] = InputFile(
                    content=await image.read(),
                    filename=image.filename,
                    unique_filename=True,
                    prefix_date=True,
                )

            # Perform the update
            stmt = update(Vehicle).where(Vehicle.id == vehicle_id).values(**update_data)

            await self.session.execute(stmt)
            await self.session.commit()

            # Refresh and return the updated vehicle
            await self.session.refresh(existing_vehicle)
            return existing_vehicle

        except IntegrityError as e:
            await self.session.rollback()
            raise e

    async def delete_vehicle(self, vehicle_id: UUID, user_id: UUID) -> bool:
        """
        Delete a vehicle record (soft delete by default).

        Args:
            session: AsyncSession database connection
            vehicle_id: UUID of the vehicle to delete
            user_id: UUID of the vehicle owner

        Returns:
            bool: True if deletion was successful, False if vehicle not found
        """
        # Check if vehicle exists and is not already soft-deleted
        existing_vehicle = await self.get_vehicle(
            vehicle_id=vehicle_id, user_id=user_id
        )
        if not existing_vehicle:
            raise InvalidRequestException("vehicle not found")

        if existing_vehicle.user_id != user_id:
            raise ForbiddenException("Not authorized to perform this action")

        existing_vehicle.soft_delete()
        await self.session.commit()
        return True


VehicleServiceDependency = Annotated[VehicleService, VehicleService.get_dependency()]
