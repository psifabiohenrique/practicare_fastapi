from http import HTTPStatus
from uuid import uuid4

import pytest

from tests.factories import TreatmentFactory, TreatmentReportFactory


@pytest.mark.asyncio
async def test_get_treatment_report(user_client, db_session):
    client, user, headers = user_client

    treatment = TreatmentFactory.build(user=user, user_uuid=user.uuid)
    db_session.add(treatment)
    await db_session.commit()
    await db_session.refresh(treatment)

    treatment_report = TreatmentReportFactory.build(treatment=treatment)
    db_session.add(treatment_report)
    await db_session.commit()
    await db_session.refresh(treatment_report)

    response = client.get(
        f"/treatment-reports/{treatment_report.uuid}", headers=headers
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["uuid"] == treatment_report.uuid
    assert data["treatment_uuid"] == treatment.uuid


@pytest.mark.asyncio
async def test_list_treatment_reports(user_client, db_session):
    client, user, headers = user_client
    batch_size = 3

    treatment = TreatmentFactory.build(user=user, user_uuid=user.uuid)
    db_session.add(treatment)
    await db_session.commit()
    await db_session.refresh(treatment)

    TreatmentReportFactory.create_batch(batch_size, treatment=treatment)
    await db_session.commit()

    response = client.get(
        f"/treatment-reports/treatment/{treatment.uuid}", headers=headers
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == batch_size


@pytest.mark.asyncio
async def test_create_treatment_report(user_client, db_session):
    client, user, headers = user_client

    treatment = TreatmentFactory.build(user=user, user_uuid=user.uuid)
    db_session.add(treatment)
    await db_session.commit()
    await db_session.refresh(treatment)

    payload = {
        "treatment_uuid": treatment.uuid,
        "demand_description": "Initial demand",
        "procedures": "Initial procedures",
        "analysis": "Initial analysis",
        "conclusion": "Initial conclusion",
        "issue_date": "2024-01-01T10:00:00",
        "start_date_period": "2024-01-01T10:00:00",
        "end_date_period": "2024-01-01T11:00:00",
    }

    response = client.post(
        "/treatment-reports/", json=payload, headers=headers
    )
    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data["demand_description"] == "Initial demand"
    assert data["treatment_uuid"] == treatment.uuid


@pytest.mark.asyncio
async def test_update_treatment_report(user_client, db_session):
    client, user, headers = user_client

    treatment = TreatmentFactory.build(user=user, user_uuid=user.uuid)
    db_session.add(treatment)
    await db_session.commit()
    await db_session.refresh(treatment)

    treatment_report = TreatmentReportFactory.build(treatment=treatment)
    db_session.add(treatment_report)
    await db_session.commit()
    await db_session.refresh(treatment_report)

    payload = {"demand_description": "Updated demand"}
    response = client.patch(
        f"/treatment-reports/{treatment_report.uuid}",
        json=payload,
        headers=headers,
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json()["demand_description"] == "Updated demand"


@pytest.mark.asyncio
async def test_get_treatment_report_forbidden(user_client, db_session):
    client, user, headers = user_client

    # Create another user and their treatment
    other_user_uuid = str(uuid4())
    treatment = TreatmentFactory.build(user_uuid=other_user_uuid)
    db_session.add(treatment)
    await db_session.commit()
    await db_session.refresh(treatment)

    treatment_report = TreatmentReportFactory.build(treatment=treatment)
    db_session.add(treatment_report)
    await db_session.commit()
    await db_session.refresh(treatment_report)

    response = client.get(
        f"/treatment-reports/{treatment_report.uuid}", headers=headers
    )
    assert response.status_code == HTTPStatus.FORBIDDEN
