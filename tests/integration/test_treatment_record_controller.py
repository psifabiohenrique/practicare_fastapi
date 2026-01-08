from http import HTTPStatus

import pytest

from tests.factories import TreatmentFactory, TreatmentRecordFactory


@pytest.mark.asyncio
async def test_get_treatment_record(user_client, db_session):
    client, user, headers = user_client

    treatment = TreatmentFactory.build(user=user, user_uuid=user.uuid)
    db_session.add(treatment)
    await db_session.commit()
    await db_session.refresh(treatment)

    treatment_record = TreatmentRecordFactory.build(treatment=treatment)
    db_session.add(treatment_record)
    await db_session.commit()
    await db_session.refresh(treatment_record)

    response = client.get(
        f"/treatment-records/{treatment_record.uuid}", headers=headers
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["uuid"] == treatment_record.uuid
    assert data["treatment_uuid"] == treatment.uuid
