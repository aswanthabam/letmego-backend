import logging
import os
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from core.db.listeners import add_loader_criteria
from apps.settings import settings
from core.db.registry import *

engine = create_async_engine(settings.DATABASE_URL)

AsyncSessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
)


async def get_session():
    async with AsyncSessionLocal() as session:
        add_loader_criteria(session)
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]

# setup logging for sqlalchamey

logger = logging.getLogger("sqlalchemy.engine")
logger.setLevel(logging.INFO)
logger.propagate = False
logger.handlers.clear()

os.makedirs("logs", exist_ok=True)

file_handler = logging.FileHandler("logs/sql.log")
file_handler.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)
