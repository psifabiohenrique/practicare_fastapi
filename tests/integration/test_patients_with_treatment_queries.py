import datetime
from http import HTTPStatus

import pytest
from freezegun import freeze_time

from models import Gender, Weekdays
from tests.factories import PatientFactory, TreatmentFactory


@pytest.mark.asyncio
async def test_pagination(user_client, db_session):
    client, user, headers = user_client
    # Create 5 treatments
    for _ in range(5):
        treatment = TreatmentFactory.build(user=user, user_uuid=user.uuid)
        db_session.add(treatment)
        await db_session.commit()

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


@pytest.mark.asyncio
async def test_ordering_by_name(user_client, db_session):
    client, user, headers = user_client
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


@pytest.mark.asyncio
async def test_filtering_by_gender(user_client, db_session):
    client, user, headers = user_client
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
        f"/patients-with-treatment/?gender={Gender.MALE.value}",
        headers=headers,
    )
    data = response.json()
    assert len(data) == 1
    assert data[0]["patient"]["gender"] == Gender.MALE.value


@pytest.mark.asyncio
async def test_search_by_name(user_client, db_session):
    client, user, headers = user_client
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
        "/patients-with-treatment/?search=Jon", headers=headers
    )
    data = response.json()
    assert len(data) == 1
    assert data[0]["patient"]["first_name"] == "Jonathan"


@pytest.mark.asyncio
@freeze_time("2025-12-29")  # It's a Monday
async def test_daily_endpoint_today(user_client, db_session):
    client, user, headers = user_client
    t1 = TreatmentFactory.build(
        user=user, user_uuid=user.uuid, weekday=Weekdays.MONDAY
    )
    t2 = TreatmentFactory.build(
        user=user, user_uuid=user.uuid, weekday=Weekdays.TUESDAY
    )
    db_session.add_all([t1, t2])
    await db_session.commit()

    response = client.get("/patients-with-treatment/daily", headers=headers)
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["weekday"] == Weekdays.MONDAY.value


@pytest.mark.asyncio
async def test_daily_endpoint_specific_day(user_client, db_session):
    client, user, headers = user_client
    t1 = TreatmentFactory.build(
        user=user, user_uuid=user.uuid, weekday=Weekdays.MONDAY
    )
    t2 = TreatmentFactory.build(
        user=user, user_uuid=user.uuid, weekday=Weekdays.TUESDAY
    )
    db_session.add_all([t1, t2])
    await db_session.commit()

    treatments_in_tuesday = 1

    response = client.get(
        f"/patients-with-treatment/daily?weekday={Weekdays.TUESDAY.value}",
        headers=headers,
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == treatments_in_tuesday
    assert data[0]["weekday"] == Weekdays.TUESDAY.value


@pytest.mark.asyncio
async def test_daily_endpoint_ordering(user_client, db_session):
    client, user, headers = user_client
    treatments_to_create = 2

    for i in range(treatments_to_create):
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
        headers=headers,
    )
    data = response.json()
    assert len(data) == treatments_to_create
    # Should be 00:00 then 01:00
    assert data[0]["start_time"] == "00:00:00"
    assert data[1]["start_time"] == "01:00:00"
