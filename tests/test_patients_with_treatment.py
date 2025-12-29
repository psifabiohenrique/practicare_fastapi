from http import HTTPStatus

from security import create_access_token
from tests.factories import TreatmentFactory, UserFactory


def test_create_patient_with_treatment(user_client):
    client, user, headers = user_client

    payload = {
        "patient_schema": {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone": "123456789",
            "birth_date": "1990-01-01",
        },
        "treatment_schema": {
            "user_uuid": "will_be_overridden",
            "patient_id": "will_be_overridden",
            "weekday": "Monday",
            "start_time": "08:00:00",
            "end_time": "09:00:00",
        },
    }

    response = client.post(
        "/patients-with-treatment/", json=payload, headers=headers
    )
    assert response.status_code == HTTPStatus.CREATED
    data = response.json()

    assert data["user_uuid"] == user.uuid
    assert data["patient"]["first_name"] == "John"
    assert data["weekday"] == "Monday"


def test_list_my_patients_with_treatment(user_client):
    client, user, headers = user_client

    number_of_treatments = 3

    # Create some treatments for this user
    TreatmentFactory.create_batch(
        number_of_treatments, user=user, user_uuid=user.uuid
    )

    # Create a treatment for another user
    TreatmentFactory()

    response = client.get("/patients-with-treatment/", headers=headers)
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == number_of_treatments
    for item in data:
        assert item["user_uuid"] == user.uuid


def test_get_treatment_details(user_client):
    client, user, headers = user_client
    treatment = TreatmentFactory(user=user, user_uuid=user.uuid)

    response = client.get(
        f"/patients-with-treatment/{treatment.id}", headers=headers
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["id"] == treatment.id
    assert data["patient"]["uuid"] == treatment.patient_id


def test_get_treatment_details_unauthorized(client, db_session):

    user1 = UserFactory()
    user2 = UserFactory()
    treatment = TreatmentFactory(user=user1, user_uuid=user1.uuid)

    token2 = create_access_token(subject=user2.id)
    headers2 = {"Authorization": f"Bearer {token2}"}

    response = client.get(
        f"/patients-with-treatment/{treatment.id}", headers=headers2
    )
    assert response.status_code == HTTPStatus.FORBIDDEN


def test_get_treatment_details_not_found(user_client):
    client, user, headers = user_client
    response = client.get("/patients-with-treatment/1", headers=headers)
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "detail" in response.json()


def test_update_patient_with_treatment(user_client):
    client, user, headers = user_client
    treatment = TreatmentFactory(user=user, user_uuid=user.uuid)

    payload = {
        "patient_schema": {"first_name": "Jane"},
        "treatment_schema": {"weekday": "Wednesday"},
    }

    response = client.patch(
        f"/patients-with-treatment/{treatment.id}",
        json=payload,
        headers=headers,
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["patient"]["first_name"] == "Jane"
    assert data["weekday"] == "Wednesday"


def test_update_treatment_unauthorized(client):

    user1 = UserFactory()
    user2 = UserFactory()
    treatment = TreatmentFactory(user=user1, user_uuid=user1.uuid)

    token2 = create_access_token(subject=user2.id)
    headers2 = {"Authorization": f"Bearer {token2}"}

    payload = {"patient_schema": {}, "treatment_schema": {"weekday": "Friday"}}

    response = client.patch(
        f"/patients-with-treatment/{treatment.id}",
        json=payload,
        headers=headers2,
    )
    assert response.status_code == HTTPStatus.FORBIDDEN


def test_update_treatment_not_found(user_client):
    client, user, headers = user_client
    payload = {"patient_schema": {}, "treatment_schema": {"weekday": "Friday"}}
    response = client.patch(
        "/patients-with-treatment/1", json=payload, headers=headers
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "detail" in response.json()
