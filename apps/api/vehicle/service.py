from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError
from typing import Optional, List, Dict, Any
from uuid import UUID

from apps.api.vehicle.models import Vehicle
from core.exceptions.authentication import (
    ForbiddenException,
)
from core.exceptions.request import (
    InvalidRequestException,
)  # Replace with your actual import path


async def create_vehicle(
    session: AsyncSession,
    vehicle_number: str,
    user_id: UUID,
    name: Optional[str] = None,
    is_verified: bool = False,
) -> Vehicle:
    """
    Create a new vehicle record.

    Args:
        session: AsyncSession database connection
        vehicle_number: Unique vehicle number
        user_id: UUID of the vehicle owner
        name: Optional vehicle name
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
            user_id=user_id,
            is_verified=is_verified,
        )

        session.add(vehicle)
        await session.commit()
        await session.refresh(vehicle)
        return vehicle

    except IntegrityError as e:
        await session.rollback()
        raise e


async def get_vehicle(
    session: AsyncSession,
    user_id: UUID,
    vehicle_id: UUID,
    include_deleted: bool = False,
) -> Optional[Vehicle]:
    """
    Get a single vehicle by ID or vehicle number.

    Args:
        session: AsyncSession database connection
        vehicle_id: UUID of the vehicle
        vehicle_number: Vehicle number to search for
        include_deleted: Whether to include soft-deleted records

    Returns:
        Vehicle or None: Found vehicle instance or None if not found
    """
    query = select(Vehicle)

    query = query.where(Vehicle.id == vehicle_id, Vehicle.user_id == user_id)

    result = await session.execute(query)
    vehicle = result.scalar()

    if not vehicle:
        raise InvalidRequestException("Vehicle not found")

    return vehicle


async def get_vehicles(
    session: AsyncSession,
    user_id: Optional[UUID] = None,
    is_verified: Optional[bool] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> List[Vehicle]:
    """
    Get multiple vehicles with optional filtering.

    Args:
        session: AsyncSession database connection
        user_id: Filter by owner user ID
        is_verified: Filter by verification status
        include_deleted: Whether to include soft-deleted records
        limit: Maximum number of records to return
        offset: Number of records to skip

    Returns:
        List[Vehicle]: List of vehicle instances
    """
    query = select(Vehicle)

    # Apply filters
    if user_id:
        query = query.where(Vehicle.user_id == user_id)

    if is_verified is not None:
        query = query.where(Vehicle.is_verified == is_verified)

    # Apply pagination
    if offset > 0:
        query = query.offset(offset)

    if limit:
        query = query.limit(limit)

    result = await session.execute(query)
    return result.scalars().all()


async def update_vehicle(
    session: AsyncSession,
    vehicle_id: UUID,
    user_id: UUID,
    vehicle_number: str,
    name: Optional[str] = None,
) -> Optional[Vehicle]:
    """
    Update a vehicle record.

    Args:
        session: AsyncSession database connection
        vehicle_id: UUID of the vehicle to update
        update_data: Dictionary containing fields to update

    Returns:
        Vehicle or None: Updated vehicle instance or None if not found

    Raises:
        IntegrityError: If update violates constraints (e.g., duplicate vehicle_number)
    """
    try:
        # First check if the vehicle exists and is not soft-deleted
        existing_vehicle = await get_vehicle(session, vehicle_id=vehicle_id)
        if not existing_vehicle:
            return None
        if existing_vehicle.user_id != user_id:
            raise ForbiddenException(
                "You do not have permission to update this vehicle."
            )

        # Perform the update
        stmt = (
            update(Vehicle)
            .where(Vehicle.id == vehicle_id)
            .values(vehicle_number=vehicle_number, name=name)
        )

        await session.execute(stmt)
        await session.commit()

        # Refresh and return the updated vehicle
        await session.refresh(existing_vehicle)
        return existing_vehicle

    except IntegrityError as e:
        await session.rollback()
        raise e


async def delete_vehicle(
    session: AsyncSession, vehicle_id: UUID, user_id: UUID
) -> bool:
    """
    Delete a vehicle record (soft delete by default).

    Args:
        session: AsyncSession database connection
        vehicle_id: UUID of the vehicle to delete
        soft_delete: Whether to perform soft delete (default: True)

    Returns:
        bool: True if deletion was successful, False if vehicle not found
    """
    # Check if vehicle exists and is not already soft-deleted
    existing_vehicle = await get_vehicle(
        session, vehicle_id=vehicle_id, user_id=user_id
    )
    if not existing_vehicle:
        raise InvalidRequestException("vehicle not found")

    if existing_vehicle.user_id != user_id:
        raise ForbiddenException("Not authorized to perform this action")

    existing_vehicle.soft_delete()
    await session.commit()
    return True


# Additional utility functions


async def get_vehicle_with_owner(
    session: AsyncSession, vehicle_id: UUID, include_deleted: bool = False
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

    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_vehicles_with_reports(
    session: AsyncSession, user_id: Optional[UUID] = None, include_deleted: bool = False
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

    result = await session.execute(query)
    return result.scalars().all()
