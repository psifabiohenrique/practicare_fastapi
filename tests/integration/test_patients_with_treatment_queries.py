import datetime
from http import HTTPStatus

from freezegun import freeze_time

from tests.factories import PatientFactory, TreatmentFactory
from utils.enums import Gender, Weekdays


def test_pagination(user_client):
    client, user, headers = user_client
    # Create 5 treatments
    for _ in range(5):
        TreatmentFactory(user=user, user_uuid=user.uuid)

    limit = 2
    response = client.get(
        f"/patients-with-treatment/?skip=0&limit={limit}", headers=headers
    )
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == limit

    response = client.get(
        f"/patients-with-treatment/?skip=2&limit={limit}", headers=headers
    )
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == limit


def test_ordering_by_name(user_client):
    client, user, headers = user_client
    p1 = PatientFactory(first_name="Alice")
    p2 = PatientFactory(first_name="Zelda")
    TreatmentFactory(
        user=user, user_uuid=user.uuid, patient=p1, patient_uuid=p1.uuid
    )
    TreatmentFactory(
        user=user, user_uuid=user.uuid, patient=p2, patient_uuid=p2.uuid
    )

    response = client.get(
        "/patients-with-treatment/?order_by=name&order_dir=asc",
        headers=headers,
    )
    data = response.json()
    assert data[0]["patient"]["first_name"] == "Alice"
    assert data[1]["patient"]["first_name"] == "Zelda"

    response = client.get(
        "/patients-with-treatment/?order_by=name&order_dir=desc",
        headers=headers,
    )
    data = response.json()
    assert data[0]["patient"]["first_name"] == "Zelda"
    assert data[1]["patient"]["first_name"] == "Alice"


def test_filtering_by_gender(user_client):
    client, user, headers = user_client
    p_male = PatientFactory(gender=Gender.MALE)
    p_female = PatientFactory(gender=Gender.FEMALE)
    TreatmentFactory(
        user=user,
        user_uuid=user.uuid,
        patient=p_male,
        patient_uuid=p_male.uuid,
    )
    TreatmentFactory(
        user=user,
        user_uuid=user.uuid,
        patient=p_female,
        patient_uuid=p_female.uuid,
    )

    response = client.get(
        f"/patients-with-treatment/?gender={Gender.MALE.value}",
        headers=headers,
    )
    data = response.json()
    assert len(data) == 1
    assert data[0]["patient"]["gender"] == Gender.MALE.value


def test_search_by_name(user_client):
    client, user, headers = user_client
    p1 = PatientFactory(first_name="Jonathan")
    p2 = PatientFactory(first_name="Maria")
    TreatmentFactory(
        user=user, user_uuid=user.uuid, patient=p1, patient_uuid=p1.uuid
    )
    TreatmentFactory(
        user=user, user_uuid=user.uuid, patient=p2, patient_uuid=p2.uuid
    )

    response = client.get(
        "/patients-with-treatment/?search=Jon", headers=headers
    )
    data = response.json()
    assert len(data) == 1
    assert data[0]["patient"]["first_name"] == "Jonathan"


@freeze_time("2025-12-29")  # It's a Monday
def test_daily_endpoint_today(user_client):
    client, user, headers = user_client
    TreatmentFactory(user=user, user_uuid=user.uuid, weekday=Weekdays.MONDAY)
    TreatmentFactory(user=user, user_uuid=user.uuid, weekday=Weekdays.TUESDAY)

    response = client.get("/patients-with-treatment/daily", headers=headers)
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["weekday"] == Weekdays.MONDAY.value


def test_daily_endpoint_specific_day(user_client):
    client, user, headers = user_client
    TreatmentFactory(user=user, user_uuid=user.uuid, weekday=Weekdays.MONDAY)
    TreatmentFactory(user=user, user_uuid=user.uuid, weekday=Weekdays.TUESDAY)

    treatments_in_tuesday = 1

    response = client.get(
        f"/patients-with-treatment/daily?weekday={Weekdays.TUESDAY.value}",
        headers=headers,
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == treatments_in_tuesday
    assert data[0]["weekday"] == Weekdays.TUESDAY.value


def test_daily_endpoint_ordering(user_client):
    client, user, headers = user_client
    treatments_to_create = 2

    for i in range(treatments_to_create):
        TreatmentFactory(
            user=user,
            user_uuid=user.uuid,
            weekday=Weekdays.MONDAY,
            start_time=datetime.time(i, 0),
        )

    response = client.get(
        f"/patients-with-treatment/daily?weekday={Weekdays.MONDAY.value}",
        headers=headers,
    )
    data = response.json()
    assert len(data) == treatments_to_create
    # Should be 00:00 then 01:00
    assert data[0]["start_time"] == "00:00:00"
    assert data[1]["start_time"] == "01:00:00"
