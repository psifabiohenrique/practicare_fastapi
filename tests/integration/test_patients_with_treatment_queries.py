import datetime
from http import HTTPStatus

import pytest
from freezegun import freeze_time

from src.models import Gender, Weekdays
from tests.factories import PatientFactory, TreatmentFactory

pytestmark = pytest.mark.asyncio


async def test_pagination(session_client, db_session):
    client, user = session_client
    for _ in range(5):
        treatment = TreatmentFactory.build(user=user, user_uuid=user.uuid)
        db_session.add(treatment)
        await db_session.commit()

    limit = 2
    response = client.get(f"/patients-with-treatment?skip=0&limit={limit}")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data["items"]) == limit
    assert data["total"] == 5

    response = client.get(f"/patients-with-treatment?skip=2&limit={limit}")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data["items"]) == limit
    assert data["total"] == 5


async def test_ordering_by_name(session_client, db_session):
    client, user = session_client
    p1 = PatientFactory.build(first_name="Alice")
    p2 = PatientFactory.build(first_name="Zelda")
    db_session.add_all([p1, p2])
    await db_session.commit()
    await db_session.refresh(p1)
    await db_session.refresh(p2)

    t1 = TreatmentFactory.build(
        user=user, user_uuid=user.uuid, patient=p1, patient_uuid=p1.uuid
    )
    t2 = TreatmentFactory.build(
        user=user, user_uuid=user.uuid, patient=p2, patient_uuid=p2.uuid
    )
    db_session.add_all([t1, t2])
    await db_session.commit()

    response = client.get(
        "/patients-with-treatment?order_by=name&order_dir=asc",
    )
    data = response.json()["items"]
    assert data[0]["patient"]["first_name"] == "Alice"
    assert data[1]["patient"]["first_name"] == "Zelda"

    response = client.get(
        "/patients-with-treatment?order_by=name&order_dir=desc",
    )
    data = response.json()["items"]
    assert data[0]["patient"]["first_name"] == "Zelda"
    assert data[1]["patient"]["first_name"] == "Alice"


async def test_filtering_by_gender(session_client, db_session):
    client, user = session_client
    p_male = PatientFactory.build(gender=Gender.MALE)
    p_female = PatientFactory.build(gender=Gender.FEMALE)
    db_session.add_all([p_male, p_female])
    await db_session.commit()
    await db_session.refresh(p_male)
    await db_session.refresh(p_female)

    t_male = TreatmentFactory.build(
        user=user,
        user_uuid=user.uuid,
        patient=p_male,
        patient_uuid=p_male.uuid,
    )
    t_female = TreatmentFactory.build(
        user=user,
        user_uuid=user.uuid,
        patient=p_female,
        patient_uuid=p_female.uuid,
    )
    db_session.add_all([t_male, t_female])
    await db_session.commit()

    response = client.get(
        f"/patients-with-treatment?gender={Gender.MALE.value}",
    )
    data = response.json()["items"]
    assert len(data) == 1
    assert data[0]["patient"]["gender"] == Gender.MALE.value


async def test_search_by_name(session_client, db_session):
    client, user = session_client
    p1 = PatientFactory.build(first_name="Jonathan")
    p2 = PatientFactory.build(first_name="Maria")
    db_session.add_all([p1, p2])
    await db_session.commit()
    await db_session.refresh(p1)
    await db_session.refresh(p2)

    t1 = TreatmentFactory.build(
        user=user, user_uuid=user.uuid, patient=p1, patient_uuid=p1.uuid
    )
    t2 = TreatmentFactory.build(
        user=user, user_uuid=user.uuid, patient=p2, patient_uuid=p2.uuid
    )
    db_session.add_all([t1, t2])
    await db_session.commit()

    response = client.get(
        "/patients-with-treatment?search=Jon",
    )
    data = response.json()["items"]
    assert len(data) == 1
    assert data[0]["patient"]["first_name"] == "Jonathan"


@freeze_time("2025-12-29")  # It's a Monday
async def test_daily_endpoint_today(session_client, db_session):
    client, user = session_client
    t1 = TreatmentFactory.build(
        user=user, user_uuid=user.uuid, weekday=Weekdays.MONDAY
    )
    t2 = TreatmentFactory.build(
        user=user, user_uuid=user.uuid, weekday=Weekdays.TUESDAY
    )
    db_session.add_all([t1, t2])
    await db_session.commit()

    response = client.get("/patients-with-treatment/daily")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["weekday"] == Weekdays.MONDAY.value


async def test_daily_endpoint_specific_day(session_client, db_session):
    client, user = session_client
    t1 = TreatmentFactory.build(
        user=user, user_uuid=user.uuid, weekday=Weekdays.MONDAY
    )
    t2 = TreatmentFactory.build(
        user=user, user_uuid=user.uuid, weekday=Weekdays.TUESDAY
    )
    db_session.add_all([t1, t2])
    await db_session.commit()

    response = client.get(
        f"/patients-with-treatment/daily?weekday={Weekdays.TUESDAY.value}",
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["weekday"] == Weekdays.TUESDAY.value


async def test_daily_endpoint_ordering(session_client, db_session):
    client, user = session_client

    for i in range(2):
        treatment = TreatmentFactory.build(
            user=user,
            user_uuid=user.uuid,
            weekday=Weekdays.MONDAY,
            start_time=datetime.time(i, 0),
        )
        db_session.add(treatment)
        await db_session.commit()

    response = client.get(
        f"/patients-with-treatment/daily?weekday={Weekdays.MONDAY.value}",
    )
    data = response.json()
    assert len(data) == 2
    assert data[0]["start_time"] == "00:00:00"
    assert data[1]["start_time"] == "01:00:00"
