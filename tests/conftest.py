import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from security import create_access_token
from tests.factories import PatientFactory, TreatmentFactory, UserFactory

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)


@pytest.fixture
def db_session():
    # Create the database tables
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    UserFactory._meta.sqlalchemy_session = session
    PatientFactory._meta.sqlalchemy_session = session
    TreatmentFactory._meta.sqlalchemy_session = session
    try:
        yield session
    finally:
        session.close()
        # Drop the database tables
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_header(db_session):
    user = UserFactory()
    access_token = create_access_token(subject=user.id)
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def user(db_session):
    return UserFactory()


@pytest.fixture
def user_client(client, db_session):
    """Returns a client and the user it's authenticated as."""
    user_obj = UserFactory()
    token = create_access_token(subject=user_obj.id)
    headers = {"Authorization": f"Bearer {token}"}
    return client, user_obj, headers
