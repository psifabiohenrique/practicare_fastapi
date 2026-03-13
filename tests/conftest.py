import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from testcontainers.postgres import PostgresContainer

from src.database import Base, get_db
from src.main import app
from src.routers.deps import csrf_protect
from src.security import create_access_token, get_password_hash
from src.services.auth_service import AuthService
from src.settings import settings
from tests.factories import (
    PatientFactory,
    TreatmentFactory,
    TreatmentRecordFactory,
    TreatmentReportFactory,
    UserFactory,
)


@pytest.fixture(autouse=True)
def mock_audio_dir(tmp_path):
    """Redirect audio operations to a temporary directory during tests."""
    settings.BASE_AUDIO_DIR = tmp_path


@pytest.fixture(scope="session")
def engine():
    with PostgresContainer("postgres:16", driver="psycopg") as postgres:
        _engine = create_async_engine(postgres.get_connection_url())
        yield _engine


@pytest_asyncio.fixture
async def db_session(engine):
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent;"))
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        UserFactory._meta.sqlalchemy_session = session
        PatientFactory._meta.sqlalchemy_session = session
        TreatmentFactory._meta.sqlalchemy_session = session
        TreatmentRecordFactory._meta.sqlalchemy_session = session
        TreatmentReportFactory._meta.sqlalchemy_session = session

        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    async def no_csrf():
        return None

    with TestClient(app) as client:
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[csrf_protect] = no_csrf
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def user(db_session):
    user_obj = UserFactory.build()
    db_session.add(user_obj)
    await db_session.commit()
    await db_session.refresh(user_obj)
    return user_obj


@pytest_asyncio.fixture
async def session_client(client, db_session):
    """Returns a (client, user) tuple authenticated via session cookies.

    The client has session_uuid cookie set and X-CSRF-Token header
    configured for mutating requests.
    """
    password = "testpassword123"
    user_obj = UserFactory.build(
        hashed_password=get_password_hash(password),
    )
    db_session.add(user_obj)
    await db_session.commit()
    await db_session.refresh(user_obj)

    session = await AuthService.create_session(
        db=db_session, user_uuid=user_obj.uuid
    )
    csrf_token = AuthService.generate_csrf_token()

    client.cookies.set("session_uuid", str(session.uuid))
    client.cookies.set("csrf_token", csrf_token)
    client.headers["X-CSRF-Token"] = csrf_token

    return client, user_obj


# --- Deprecated JWT fixtures (kept for legacy JWT endpoint tests) ---


@pytest_asyncio.fixture
async def auth_header(db_session):
    """Deprecated: Use session_client instead.
    Kept for backward compatibility with JWT endpoint tests."""
    user = UserFactory.build()
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    access_token = create_access_token(subject=user.uuid)
    return {"Authorization": f"Bearer {access_token}"}


@pytest_asyncio.fixture
async def user_client(client, db_session):
    """Deprecated: Use session_client instead.
    Kept for backward compatibility with JWT endpoint tests."""
    user_obj = UserFactory.build()
    db_session.add(user_obj)
    await db_session.commit()
    await db_session.refresh(user_obj)

    token = create_access_token(subject=user_obj.uuid)
    headers = {"Authorization": f"Bearer {token}"}
    return client, user_obj, headers
