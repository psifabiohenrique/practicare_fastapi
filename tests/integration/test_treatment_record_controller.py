from http import HTTPStatus

from tests.factories import TreatmentFactory, TreatmentRecordFactory


def test_get_treatment_record(user_client):
    client, user, headers = user_client

    treatment = TreatmentFactory(user=user, user_uuid=user.uuid)
    treatment_record = TreatmentRecordFactory(treatment=treatment)

    response = client.get(
        f"/treatment-records/{treatment_record.uuid}", headers=headers
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    print(data)
    assert data["uuid"] == treatment_record.uuid
    assert data["treatment_uuid"] == treatment.uuid
