from http import HTTPStatus

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.models import (
    Patient,
    Treatment,
    TreatmentRecord,
    TreatmentReport,
    User,
)
from tests.factories import (
    PatientFactory,
    TreatmentFactory,
    TreatmentRecordFactory,
    TreatmentReportFactory,
    UserFactory,
)


@pytest.mark.asyncio
async def test_create_user(db_session):
    user = UserFactory.build()
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

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
    patient = PatientFactory.build()
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)

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

    treatment = TreatmentFactory.build()
    db_session.add(treatment)
    await db_session.commit()

    # Load with relationships
    result = await db_session.execute(
        select(Treatment)
        .options(selectinload(Treatment.user), selectinload(Treatment.patient))
        .filter(Treatment.id == treatment.id)
    )
    treatment = result.scalars().first()

    assert treatment.id is not None
    assert treatment.user_uuid is not None
    assert treatment.patient_uuid is not None

    # Test relationships
    assert treatment.user is not None
    assert treatment.patient is not None

    # Load reverse relationships
    await db_session.refresh(treatment.user, ["treatments"])
    await db_session.refresh(treatment.patient, ["treatments"])

    assert treatment in treatment.user.treatments
    assert treatment in treatment.patient.treatments


@pytest.mark.asyncio
async def test_create_treatment_record(db_session):

    record = TreatmentRecordFactory.build()
    db_session.add(record)
    await db_session.commit()

    # Load with relationships
    result = await db_session.execute(
        select(TreatmentRecord)
        .options(selectinload(TreatmentRecord.treatment))
        .filter(TreatmentRecord.id == record.id)
    )
    record = result.scalars().first()

    assert record.id is not None
    assert record.uuid is not None
    assert record.treatment_uuid is not None
    assert record.content is not None
    assert record.record_number is not None

    # Test relationships
    assert record.treatment is not None
    await db_session.refresh(record.treatment, ["treatment_records"])
    assert record in record.treatment.treatment_records


@pytest.mark.asyncio
async def test_create_treatment_report(db_session):

    report = TreatmentReportFactory.build()
    db_session.add(report)
    await db_session.commit()

    # Load with relationships
    result = await db_session.execute(
        select(TreatmentReport)
        .options(selectinload(TreatmentReport.treatment))
        .filter(TreatmentReport.id == report.id)
    )
    report = result.scalars().first()

    assert report.id is not None
    assert report.uuid is not None
    assert report.treatment_uuid is not None
    assert report.demand_description is not None

    # Test relationships
    assert report.treatment is not None
    await db_session.refresh(report.treatment, ["treatment_reports"])
    assert report in report.treatment.treatment_reports


def test_root_endpoint(client):
    response = client.get("")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"Hello": "World"}
