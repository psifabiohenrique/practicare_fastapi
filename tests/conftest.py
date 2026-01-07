import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from testcontainers.postgres import PostgresContainer

from database import Base, get_db
from main import app
from security import create_access_token
from tests.factories import PatientFactory, TreatmentFactory, UserFactory


@pytest.fixture(scope="session")
def engine():
    with PostgresContainer("postgres:16", driver="psycopg") as postgres:
        _engine = create_async_engine(postgres.get_connection_url())
        yield _engine


@pytest_asyncio.fixture
async def db_session(engine):
    # Create the database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        # Update factories to use this session (though async is limited)
        UserFactory._meta.sqlalchemy_session = session
        PatientFactory._meta.sqlalchemy_session = session
        TreatmentFactory._meta.sqlalchemy_session = session

        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    with TestClient(app) as client:
        app.dependency_overrides[get_db] = override_get_db
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_header(db_session):
    user = UserFactory.build()
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    access_token = create_access_token(subject=user.uuid)
    return {"Authorization": f"Bearer {access_token}"}


@pytest_asyncio.fixture
async def user(db_session):
    user_obj = UserFactory.build()
    db_session.add(user_obj)
    await db_session.commit()
    await db_session.refresh(user_obj)
    return user_obj


@pytest_asyncio.fixture
async def user_client(client, db_session):
    """Returns a client and the user it's authenticated as."""
    user_obj = UserFactory.build()
    db_session.add(user_obj)
    await db_session.commit()
    await db_session.refresh(user_obj)

    token = create_access_token(subject=user_obj.uuid)
    headers = {"Authorization": f"Bearer {token}"}
    return client, user_obj, headers
