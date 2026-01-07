from http import HTTPStatus

import pytest
from sqlalchemy import select

from models import Patient, Treatment, TreatmentRecord, TreatmentReport, User
from tests.factories import (
    PatientFactory,
    TreatmentFactory,
    TreatmentRecordFactory,
    TreatmentReportFactory,
    UserFactory,
)


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


@pytest.mark.asyncio
async def test_create_treatment_record(db_session):
    record = TreatmentRecordFactory()
    assert record.id is not None
    assert record.uuid is not None
    assert record.treatment_uuid is not None
    assert record.content is not None
    assert record.record_number is not None

    result = await db_session.execute(
        select(TreatmentRecord).filter(TreatmentRecord.id == record.id)
    )
    db_record = result.scalars().first()
    assert db_record.uuid == record.uuid
    assert db_record.treatment_uuid == record.treatment_uuid

    # Test relationships
    assert record.treatment is not None
    assert record in record.treatment.treatment_records


@pytest.mark.asyncio
async def test_create_treatment_report(db_session):
    report = TreatmentReportFactory()
    assert report.id is not None
    assert report.uuid is not None
    assert report.treatment_uuid is not None
    assert report.demand_description is not None

    result = await db_session.execute(
        select(TreatmentReport).filter(TreatmentReport.id == report.id)
    )
    db_report = result.scalars().first()
    assert db_report.uuid == report.uuid
    assert db_report.treatment_uuid == report.treatment_uuid

    # Test relationships
    assert report.treatment is not None
    assert report in report.treatment.treatment_reports


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"Hello": "World"}
