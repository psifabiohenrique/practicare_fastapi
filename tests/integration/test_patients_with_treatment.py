import uuid as uuid_pkg
from http import HTTPStatus

import pytest

from src.models import TreatmentStatus
from src.security import get_password_hash
from src.services.auth_service import AuthService
from tests.factories import TreatmentFactory, UserFactory

pytestmark = pytest.mark.asyncio


async def test_create_patient_with_treatment(session_client):
    client, user = session_client
    payload = {
        "patient_schema": {
            "first_name": "Valid",
            "last_name": "Phone",
            "email": "john@example.com",
            "phone": "11999999999",
            "birth_date": "1990-01-01",
        },
        "treatment_schema": {
            "weekday": "Monday",
            "start_time": "08:00:00",
            "end_time": "09:00:00",
        },
    }

    response = client.post("/patients-with-treatment", json=payload)
    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data["patient"]["phone"] == "+5511999999999"
    assert data["user_uuid"] == str(user.uuid)
    assert data["patient"]["first_name"] == "Valid"
    assert data["weekday"] == "Monday"


async def test_list_my_patients_with_treatment(session_client, db_session):
    client, user = session_client
    number_of_treatments = 3

    treatments = TreatmentFactory.build_batch(
        number_of_treatments, user=user, user_uuid=user.uuid
    )
    db_session.add_all(treatments)
    await db_session.commit()

    # Create a treatment for another user
    other_treatment = TreatmentFactory.build()
    db_session.add(other_treatment)
    await db_session.commit()

    response = client.get("/patients-with-treatment")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == number_of_treatments
    for item in data:
        assert item["user_uuid"] == str(user.uuid)


async def test_get_treatment_details(session_client, db_session):
    client, user = session_client
    treatment = TreatmentFactory.build(user=user, user_uuid=user.uuid)
    db_session.add(treatment)
    await db_session.commit()
    await db_session.refresh(treatment)

    response = client.get(f"/patients-with-treatment/{treatment.uuid}")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["uuid"] == str(treatment.uuid)
    assert data["patient"]["uuid"] == str(treatment.patient_uuid)


async def test_get_treatment_details_unauthorized(client, db_session):
    """A session user trying to access another user's treatment."""
    user1 = UserFactory.build(
        hashed_password=get_password_hash("pw"),
    )
    user2 = UserFactory.build(
        hashed_password=get_password_hash("pw"),
    )
    db_session.add_all([user1, user2])
    await db_session.commit()
    await db_session.refresh(user1)
    await db_session.refresh(user2)

    treatment = TreatmentFactory.build(user=user1, user_uuid=user1.uuid)
    db_session.add(treatment)
    await db_session.commit()
    await db_session.refresh(treatment)

    # Authenticate as user2
    session2 = await AuthService.create_session(db_session, user2.uuid)
    csrf_token = AuthService.generate_csrf_token()
    client.cookies.set("session_uuid", str(session2.uuid))
    client.cookies.set("csrf_token", csrf_token)
    client.headers["X-CSRF-Token"] = csrf_token

    response = client.get(f"/patients-with-treatment/{treatment.uuid}")
    assert response.status_code == HTTPStatus.FORBIDDEN


async def test_get_treatment_details_not_found(session_client):
    client, _ = session_client
    random_uuid = str(uuid_pkg.uuid4())
    response = client.get(f"/patients-with-treatment/{random_uuid}")
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "detail" in response.json()


async def test_update_patient_with_treatment(session_client, db_session):
    client, user = session_client
    treatment = TreatmentFactory.build(user=user, user_uuid=user.uuid)
    db_session.add(treatment)
    await db_session.commit()
    await db_session.refresh(treatment)

    payload = {
        "patient_schema": {"first_name": "Jane"},
        "treatment_schema": {"weekday": "Wednesday"},
    }

    response = client.patch(
        f"/patients-with-treatment/{treatment.uuid}",
        json=payload,
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["patient"]["first_name"] == "Jane"
    assert data["weekday"] == "Wednesday"


async def test_update_patient_with_treatment_phone_normalization(
    session_client, db_session
):
    client, user = session_client
    treatment = TreatmentFactory.build(user=user, user_uuid=user.uuid)
    db_session.add(treatment)
    await db_session.commit()
    await db_session.refresh(treatment)

    payload = {
        "patient_schema": {"first_name": "Valid", "phone": "11999999999"},
        "treatment_schema": {"weekday": "Wednesday"},
    }

    response = client.patch(
        f"/patients-with-treatment/{treatment.uuid}",
        json=payload,
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["patient"]["phone"] == "+5511999999999"


async def test_update_treatment_unauthorized(client, db_session):
    user1 = UserFactory.build(
        hashed_password=get_password_hash("pw"),
    )
    user2 = UserFactory.build(
        hashed_password=get_password_hash("pw"),
    )
    db_session.add_all([user1, user2])
    await db_session.commit()
    await db_session.refresh(user1)
    await db_session.refresh(user2)

    treatment = TreatmentFactory.build(user=user1, user_uuid=user1.uuid)
    db_session.add(treatment)
    await db_session.commit()
    await db_session.refresh(treatment)

    # Authenticate as user2
    session2 = await AuthService.create_session(db_session, user2.uuid)
    csrf_token = AuthService.generate_csrf_token()
    client.cookies.set("session_uuid", str(session2.uuid))
    client.cookies.set("csrf_token", csrf_token)
    client.headers["X-CSRF-Token"] = csrf_token

    payload = {"patient_schema": {}, "treatment_schema": {"weekday": "Friday"}}

    response = client.patch(
        f"/patients-with-treatment/{treatment.uuid}",
        json=payload,
    )
    assert response.status_code == HTTPStatus.FORBIDDEN


async def test_update_treatment_not_found(session_client):
    client, _ = session_client
    payload = {"patient_schema": {}, "treatment_schema": {"weekday": "Friday"}}
    random_uuid = str(uuid_pkg.uuid4())
    response = client.patch(
        f"/patients-with-treatment/{random_uuid}",
        json=payload,
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "detail" in response.json()


async def test_update_treatment_restricted_fields(session_client, db_session):
    client, user = session_client
    treatment = TreatmentFactory.build(user=user, user_uuid=user.uuid)
    db_session.add(treatment)
    await db_session.commit()
    await db_session.refresh(treatment)

    initial_user_uuid = treatment.user_uuid
    initial_patient_uuid = treatment.patient_uuid

    payload = {
        "patient_schema": {},
        "treatment_schema": {
            "user_uuid": "some-other-uuid",
            "patient_uuid": "some-other-patient-uuid",
            "weekday": "Thursday",
        },
    }

    response = client.patch(
        f"/patients-with-treatment/{treatment.uuid}",
        json=payload,
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["weekday"] == "Thursday"
    assert data["user_uuid"] == str(initial_user_uuid)
    assert data["patient"]["uuid"] == str(initial_patient_uuid)


async def test_update_patient_with_treatment_with_invalid_phone(
    session_client, db_session
):
    client, user = session_client
    treatment = TreatmentFactory.build(user=user, user_uuid=user.uuid)
    db_session.add(treatment)
    await db_session.commit()
    await db_session.refresh(treatment)

    payload = {
        "patient_schema": {"first_name": "Valid", "phone": "123"},
        "treatment_schema": {"weekday": "Wednesday"},
    }

    response = client.patch(
        f"/patients-with-treatment/{treatment.uuid}",
        json=payload,
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    data = response.json()
    assert "Invalid phone number" in data["detail"]


async def test_create_patient_with_invalid_phone(session_client):
    client, _ = session_client
    payload = {
        "patient_schema": {
            "first_name": "Invalid",
            "last_name": "Phone",
            "email": "john@example.com",
            "phone": "123",
            "birth_date": "1990-01-01",
        },
        "treatment_schema": {
            "weekday": "Monday",
            "start_time": "08:00:00",
            "end_time": "09:00:00",
        },
    }

    response = client.post("/patients-with-treatment", json=payload)
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "Invalid phone number" in response.json()["detail"]


async def test_delete_patient_with_treatment(session_client, db_session):
    client, user = session_client
    treatment = TreatmentFactory.build(
        user=user, user_uuid=user.uuid, status=TreatmentStatus.ACTIVE
    )
    db_session.add(treatment)
    await db_session.commit()
    await db_session.refresh(treatment)

    response = client.post(f"/patients-with-treatment/{treatment.uuid}")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["status"] == TreatmentStatus.INACTIVE

    # Verify in DB
    await db_session.refresh(treatment)
    assert treatment.status == TreatmentStatus.INACTIVE


async def test_delete_patient_with_treatment_toggles_back(
    session_client, db_session
):
    client, user = session_client
    treatment = TreatmentFactory.build(
        user=user, user_uuid=user.uuid, status=TreatmentStatus.INACTIVE
    )
    db_session.add(treatment)
    await db_session.commit()
    await db_session.refresh(treatment)

    response = client.post(f"/patients-with-treatment/{treatment.uuid}")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["status"] == TreatmentStatus.ACTIVE


async def test_delete_treatment_unauthorized(client, db_session):
    user1 = UserFactory.build(
        hashed_password=get_password_hash("pw"),
    )
    user2 = UserFactory.build(
        hashed_password=get_password_hash("pw"),
    )
    db_session.add_all([user1, user2])
    await db_session.commit()
    await db_session.refresh(user1)
    await db_session.refresh(user2)

    treatment = TreatmentFactory.build(user=user1, user_uuid=user1.uuid)
    db_session.add(treatment)
    await db_session.commit()
    await db_session.refresh(treatment)

    # Authenticate as user2
    session2 = await AuthService.create_session(db_session, user2.uuid)
    csrf_token = AuthService.generate_csrf_token()
    client.cookies.set("session_uuid", str(session2.uuid))
    client.cookies.set("csrf_token", csrf_token)
    client.headers["X-CSRF-Token"] = csrf_token

    response = client.post(f"/patients-with-treatment/{treatment.uuid}")
    assert response.status_code == HTTPStatus.FORBIDDEN


async def test_delete_treatment_not_found(session_client):
    client, _ = session_client
    random_uuid = str(uuid_pkg.uuid4())
    response = client.post(f"/patients-with-treatment/{random_uuid}")
    assert response.status_code == HTTPStatus.NOT_FOUND
