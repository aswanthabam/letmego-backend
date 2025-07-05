# apps/vehicle/service.py
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError
from typing import Annotated, Optional, List, Dict, Any
from uuid import UUID, uuid4
from fastapi import UploadFile
import io

from apps.api.vehicle.models import Vehicle, VehicleType
from core.architecture.service import AbstractService
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
    def __init__(self, session):
        super().__init__(session)

    async def create_vehicle(
        self,
        vehicle_number: str,
        user_id: UUID,
        name: Optional[str] = None,
        vehicle_type: Optional[VehicleType] = None,
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
            vehicle = Vehicle(
                vehicle_number=vehicle_number,
                name=name,
                vehicle_type=vehicle_type,
                brand=brand,
                user_id=user_id,
                is_verified=is_verified,
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
        user_id: UUID,
        vehicle_id: UUID,
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
        query = select(Vehicle)

        query = query.where(Vehicle.id == vehicle_id, Vehicle.user_id == user_id)

        if not include_deleted:
            query = query.where(Vehicle.deleted_at.is_(None))

        result = await self.session.execute(query)
        vehicle = result.scalar()

        if not vehicle:
            raise InvalidRequestException("Vehicle not found")

        return vehicle

    async def get_vehicles(
        self,
        user_id: Optional[UUID] = None,
        vehicle_type: Optional[VehicleType] = None,
        brand: Optional[str] = None,
        is_verified: Optional[bool] = None,
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

        if brand:
            query = query.where(Vehicle.brand.ilike(f"%{brand}%"))

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
        vehicle_type: Optional[VehicleType] = None,
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

    # Additional utility functions

    async def get_vehicle_with_owner(
        self, vehicle_id: UUID, include_deleted: bool = False
    ) -> Optional[Vehicle]:
        """
        Get a vehicle with its owner relationship loaded.

        Args:
            session: AsyncSession database connection
            vehicle_id: UUID of the vehicle
            include_deleted: Whether to include soft-deleted records

        Returns:
            Vehicle or None: Vehicle instance with owner loaded
        """
        from sqlalchemy.orm import selectinload

        query = select(Vehicle).options(selectinload(Vehicle.owner))
        query = query.where(Vehicle.id == vehicle_id)

        if not include_deleted:
            query = query.where(Vehicle.deleted_at.is_(None))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_vehicles_with_reports(
        self, user_id: Optional[UUID] = None, include_deleted: bool = False
    ) -> List[Vehicle]:
        """
        Get vehicles with their reports relationship loaded.

        Args:
            session: AsyncSession database connection
            user_id: Optional filter by owner user ID
            include_deleted: Whether to include soft-deleted records

        Returns:
            List[Vehicle]: List of vehicles with reports loaded
        """
        from sqlalchemy.orm import selectinload

        query = select(Vehicle).options(selectinload(Vehicle.reports))

        if user_id:
            query = query.where(Vehicle.user_id == user_id)

        if not include_deleted:
            query = query.where(Vehicle.deleted_at.is_(None))

        result = await self.session.execute(query)
        return result.scalars().all()

    async def search_vehicles(
        self,
        search_term: str,
        user_id: Optional[UUID] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Vehicle]:
        """
        Search vehicles by vehicle number, name, or brand.

        Args:
            session: AsyncSession database connection
            search_term: Search term to match against vehicle fields
            user_id: Optional filter by owner user ID
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List[Vehicle]: List of matching vehicle instances
        """
        query = select(Vehicle)

        # Search in vehicle_number, name, and brand
        search_filter = (
            Vehicle.vehicle_number.ilike(f"%{search_term}%")
            | Vehicle.name.ilike(f"%{search_term}%")
            | Vehicle.brand.ilike(f"%{search_term}%")
        )
        query = query.where(search_filter)

        if user_id:
            query = query.where(Vehicle.user_id == user_id)

        # Only include non-deleted records
        query = query.where(Vehicle.deleted_at.is_(None))

        # Apply pagination
        if offset > 0:
            query = query.offset(offset)

        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()


VehicleServiceDependency = Annotated[VehicleService, VehicleService.get_dependency()]
