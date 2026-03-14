from http import HTTPStatus
from uuid import uuid4

import pytest

from tests.factories import TreatmentFactory, TreatmentRecordFactory

pytestmark = pytest.mark.asyncio


async def test_get_treatment_record(session_client, db_session):
    client, user = session_client

    treatment = TreatmentFactory.build(user=user, user_uuid=user.uuid)
    db_session.add(treatment)
    await db_session.commit()
    await db_session.refresh(treatment)

    treatment_record = TreatmentRecordFactory.build(
        treatment=treatment, record_number=1
    )
    db_session.add(treatment_record)
    await db_session.commit()
    await db_session.refresh(treatment_record)

    response = client.get(f"/treatment-records/{treatment_record.uuid}")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["uuid"] == str(treatment_record.uuid)
    assert data["treatment_uuid"] == str(treatment.uuid)


async def test_list_treatment_records(session_client, db_session):
    client, user = session_client
    batch_size = 3

    treatment = TreatmentFactory.build(user=user, user_uuid=user.uuid)
    db_session.add(treatment)
    await db_session.commit()
    await db_session.refresh(treatment)

    TreatmentRecordFactory.create_batch(batch_size, treatment=treatment)
    await db_session.commit()

    response = client.get(f"/treatment-records/treatment/{treatment.uuid}")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == batch_size


async def test_create_treatment_record_sequential(session_client, db_session):
    client, user = session_client

    treatment = TreatmentFactory.build(user=user, user_uuid=user.uuid)
    db_session.add(treatment)
    await db_session.commit()
    await db_session.refresh(treatment)

    payload = {
        "treatment_uuid": str(treatment.uuid),
        "date": "2024-01-01",
        "start_time": "10:00:00",
        "end_time": "11:00:00",
        "content": "Record 1",
    }

    # First record
    response = client.post("/treatment-records", json=payload)
    assert response.status_code == HTTPStatus.CREATED
    assert response.json()["record_number"] == 1

    # Second record
    payload["content"] = "Record 2"
    response = client.post("/treatment-records", json=payload)
    assert response.status_code == HTTPStatus.CREATED
    assert response.json()["record_number"] == 2  # noqa: PLR2004


async def test_update_treatment_record(session_client, db_session):
    client, user = session_client

    treatment = TreatmentFactory.build(user=user, user_uuid=user.uuid)
    db_session.add(treatment)
    await db_session.commit()
    await db_session.refresh(treatment)

    treatment_record = TreatmentRecordFactory.build(
        treatment=treatment, record_number=1
    )
    db_session.add(treatment_record)
    await db_session.commit()
    await db_session.refresh(treatment_record)

    payload = {"content": "Updated content"}
    response = client.patch(
        f"/treatment-records/{treatment_record.uuid}",
        json=payload,
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json()["content"] == "Updated content"


async def test_get_treatment_record_forbidden(session_client, db_session):
    client, user = session_client

    # Create another user and their treatment
    other_user_uuid = str(uuid4())
    treatment = TreatmentFactory.build(user_uuid=other_user_uuid)
    db_session.add(treatment)
    await db_session.commit()
    await db_session.refresh(treatment)

    treatment_record = TreatmentRecordFactory.build(
        treatment=treatment, record_number=1
    )
    db_session.add(treatment_record)
    await db_session.commit()
    await db_session.refresh(treatment_record)

    response = client.get(f"/treatment-records/{treatment_record.uuid}")
    assert response.status_code == HTTPStatus.FORBIDDEN


async def test_get_treatment_record_not_found(session_client):
    client, _ = session_client
    random_uuid = str(uuid4())
    response = client.get(f"/treatment-records/{random_uuid}")
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "detail" in response.json()
