from typing import Annotated, Type, TypeVar, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from core.db.core import SessionDep  # Alias for Depends(get_db) or similar

T = TypeVar("T", bound="AbstractService")


class AbstractService:
    def __init__(self, session: AsyncSession):
        """
        Initialize the service with an AsyncSession.

        :param session: SQLAlchemy AsyncSession instance.
        """
        self.session = session

    @classmethod
    def _get_dependency_function(cls: Type[T], session: SessionDep) -> T:
        """
        Internal method to return a class instance as a dependency.

        This is designed to be used internally by FastAPI's `Depends()`.
        It accepts the database session and returns an instance of the service.

        :param session: The async database session (injected by FastAPI).
        :return: An instance of the service class.
        """
        return cls(session=session)

    @classmethod
    def get_dependency(cls: Type[T]) -> Callable[..., T]:
        """
        Returns a FastAPI dependency for this service.

        This can be used in route definitions to inject the service automatically.
        """
        return Depends(cls._get_dependency_function)
