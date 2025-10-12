# apps/api/shop/service.py

from sqlalchemy import select, update, delete
import sqlalchemy as sa
from typing import Annotated, Optional, List
from uuid import UUID

from apps.api.shop.models import Shop
from apps.api.shop.schema import ShopCreate, ShopUpdate
from avcfastapi.core.database.sqlalchamey.core import SessionDep
from avcfastapi.core.exception.request import InvalidRequestException
from avcfastapi.core.fastapi.dependency.service_dependency import AbstractService


class ShopService(AbstractService):
    DEPENDENCIES = {"session": SessionDep}

    def __init__(self, session: SessionDep, **kwargs):
        super().__init__(session=session, **kwargs)
        self.session = session

    async def create_shop(self, shop_data: ShopCreate) -> Shop:
        """
        Create a new shop.

        Args:
            shop_data: ShopCreate schema with shop details

        Returns:
            Shop: Created shop instance
        """
        shop = Shop(**shop_data.model_dump())
        self.session.add(shop)
        await self.session.commit()
        await self.session.refresh(shop)
        return shop

    async def get_shop(self, shop_id: UUID) -> Optional[Shop]:
        """
        Get a shop by ID.

        Args:
            shop_id: UUID of the shop

        Returns:
            Shop or None if not found
        """
        result = await self.session.execute(
            select(Shop).where(Shop.id == shop_id, Shop.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_shops(
        self,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[List[Shop], int]:
        """
        Get list of shops with optional filters.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            category: Filter by category
            is_active: Filter by active status

        Returns:
            Tuple of (list of shops, total count)
        """
        query = select(Shop).where(Shop.deleted_at.is_(None))

        if category:
            query = query.where(Shop.category == category)
        if is_active is not None:
            query = query.where(Shop.is_active == is_active)

        # Get total count
        count_result = await self.session.execute(
            select(sa.func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        # Get paginated results
        query = query.offset(skip).limit(limit).order_by(Shop.created_at.desc())
        result = await self.session.execute(query)
        shops = result.scalars().all()

        return list(shops), total

    async def update_shop(self, shop_id: UUID, shop_data: ShopUpdate) -> Shop:
        """
        Update an existing shop.

        Args:
            shop_id: UUID of the shop to update
            shop_data: ShopUpdate schema with updated fields

        Returns:
            Updated shop instance

        Raises:
            InvalidRequestException: If shop not found
        """
        shop = await self.get_shop(shop_id)
        if not shop:
            raise InvalidRequestException(
                "Shop not found",
                error_code="SHOP_NOT_FOUND",
            )

        # Update only provided fields
        update_data = shop_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(shop, field, value)

        await self.session.commit()
        await self.session.refresh(shop)
        return shop

    async def delete_shop(self, shop_id: UUID) -> bool:
        """
        Soft delete a shop.

        Args:
            shop_id: UUID of the shop to delete

        Returns:
            True if deleted successfully

        Raises:
            InvalidRequestException: If shop not found
        """
        shop = await self.get_shop(shop_id)
        if not shop:
            raise InvalidRequestException(
                "Shop not found",
                error_code="SHOP_NOT_FOUND",
            )

        # Soft delete using the mixin
        await shop.delete(self.session)
        await self.session.commit()
        return True


ShopServiceDependency = Annotated[ShopService, ShopService.get_dependency()]
