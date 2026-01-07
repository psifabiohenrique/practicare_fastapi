from http import HTTPStatus

import pytest
from sqlalchemy import select

from models import Patient, Treatment, User
from tests.factories import PatientFactory, TreatmentFactory, UserFactory


@pytest.mark.asyncio
async def test_create_user(db_session):
    user = UserFactory()

    assert user.id is not None
    assert user.uuid is not None
    assert user.name is not None
    assert user.email is not None
    assert user.hashed_password is not None

    # Verify persistence
    result = await db_session.execute(select(User).filter(User.id == user.id))
    db_user = result.scalars().first()
    assert db_user.email == user.email


@pytest.mark.asyncio
async def test_create_patient(db_session):
    patient = PatientFactory()
    assert patient.id is not None
    assert patient.uuid is not None
    assert patient.first_name is not None

    result = await db_session.execute(
        select(Patient).filter(Patient.id == patient.id)
    )
    db_patient = result.scalars().first()
    assert db_patient.uuid == patient.uuid
    assert db_patient.gender == patient.gender


@pytest.mark.asyncio
async def test_create_treatment(db_session):
    treatment = TreatmentFactory()
    assert treatment.id is not None
    assert treatment.user_uuid is not None
    assert treatment.patient_uuid is not None

    result = await db_session.execute(
        select(Treatment).filter(Treatment.id == treatment.id)
    )
    db_treatment = result.scalars().first()
    assert db_treatment.user_uuid == treatment.user_uuid
    assert db_treatment.patient_uuid == treatment.patient_uuid

    # Test relationships
    assert treatment.user is not None
    assert treatment.patient is not None
    assert treatment in treatment.user.treatments
    assert treatment in treatment.patient.treatments


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"Hello": "World"}
