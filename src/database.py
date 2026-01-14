from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from settings import settings

engine = create_async_engine(settings.DATABASE_URL)
SessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)

Base = declarative_base()


async def get_db():  # pragma: no cover
    async with SessionLocal() as session:
        yield session


async def get_async_session() -> AsyncSession:
    return SessionLocal()
