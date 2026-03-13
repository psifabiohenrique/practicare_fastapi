from datetime import date, time
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.models import Gender, TreatmentStatus, Weekdays
from src.schemas.auth_schema import LoginRequest
from src.schemas.message_schema import Details, Message
from src.schemas.patient_schema import (
    PatientCreate,
    PatientRead,
    PatientUpdate,
)
from src.schemas.patient_with_treatment_schema import (
    PatientWithTreatmentCreate,
    PatientWithTreatmentUpdate,
)
from src.schemas.token_schema import Token, TokenCSRF, TokenPayload
from src.schemas.treatment_record_schema import (
    TreatmentRecordCreate,
    TreatmentRecordUpdate,
)
from src.schemas.treatment_report_schema import (
    AutomatedReportCreate,
    TreatmentReportCreate,
    TreatmentReportUpdate,
)
from src.schemas.treatment_schema import (
    TreatmentCreate,
    TreatmentRead,
    TreatmentUpdate,
    TreatmentUpdateInternal,
)
from src.schemas.user_schema import UserCreate, UserRead, UserUpdate


class TestLoginRequestSchema:
    def test_valid_login(self):
        login = LoginRequest(email="user@example.com", password="secret")
        assert login.email == "user@example.com"
        assert login.password == "secret"

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="not-an-email", password="secret")

    def test_missing_password(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="user@example.com")


class TestUserSchemas:
    def test_user_create(self):
        user = UserCreate(
            email="test@example.com",
            name="Test",
            password="pw123",
            password_confirmation="pw123",
        )
        assert user.email == "test@example.com"
        assert user.password == "pw123"

    def test_user_create_invalid_email(self):
        with pytest.raises(ValidationError):
            UserCreate(
                email="invalid",
                name="Test",
                password="pw",
                password_confirmation="pw",
            )

    def test_user_read(self):
        uid = uuid4()
        user = UserRead(uuid=uid, email="a@b.com", name="A")
        assert user.uuid == uid

    def test_user_update_partial(self):
        update = UserUpdate(name="Updated")
        data = update.model_dump(exclude_unset=True)
        assert data == {"name": "Updated"}
        assert "email" not in data


class TestPatientSchemas:
    def test_patient_create(self):
        p = PatientCreate(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone="11999999999",
            birth_date=date(1990, 1, 1),
            gender=Gender.MALE,
        )
        assert p.first_name == "John"
        assert p.gender == Gender.MALE

    def test_patient_create_minimal(self):
        p = PatientCreate(first_name="Jane", last_name="Doe")
        assert p.email is None
        assert p.phone is None
        assert p.birth_date is None
        assert p.gender is None

    def test_patient_update_partial(self):
        update = PatientUpdate(first_name="Updated")
        data = update.model_dump(exclude_unset=True)
        assert data == {"first_name": "Updated"}

    def test_patient_read(self):
        uid = uuid4()
        p = PatientRead(
            uuid=uid,
            first_name="John",
            last_name="Doe",
            full_name="John Doe",
        )
        assert p.uuid == uid
        assert p.full_name == "John Doe"


class TestTreatmentSchemas:
    def test_treatment_create(self):
        t = TreatmentCreate(
            weekday=Weekdays.MONDAY,
            start_time=time(9, 0),
            end_time=time(10, 0),
        )
        assert t.weekday == Weekdays.MONDAY

    def test_treatment_read(self):
        uid = uuid4()
        t = TreatmentRead(
            uuid=uid,
            user_uuid=uuid4(),
            patient_uuid=uuid4(),
            weekday=Weekdays.FRIDAY,
            start_time=time(14, 0),
            end_time=time(15, 0),
            status=TreatmentStatus.ACTIVE,
        )
        assert t.status == TreatmentStatus.ACTIVE

    def test_treatment_update_partial(self):
        update = TreatmentUpdate(weekday=Weekdays.WEDNESDAY)
        data = update.model_dump(exclude_unset=True)
        assert data == {"weekday": Weekdays.WEDNESDAY}

    def test_treatment_update_internal_default_status(self):
        update = TreatmentUpdateInternal()
        assert update.status == TreatmentStatus.ACTIVE


class TestTreatmentRecordSchemas:
    def test_treatment_record_create(self):
        r = TreatmentRecordCreate(
            treatment_uuid=uuid4(),
            date=date(2024, 1, 1),
            start_time=time(10, 0),
            end_time=time(11, 0),
            content="Session notes",
        )
        assert r.content == "Session notes"

    def test_treatment_record_update_partial(self):
        update = TreatmentRecordUpdate(content="Updated notes")
        data = update.model_dump(exclude_unset=True)
        assert data == {"content": "Updated notes"}


class TestTreatmentReportSchemas:
    def test_treatment_report_create(self):
        uid = uuid4()
        r = TreatmentReportCreate(
            treatment_uuid=uid,
            demand_description="demand",
            procedures="procs",
            analysis="analysis",
            conclusion="conclusion",
            issue_date=date(2024, 1, 1),
            start_date_period=date(2024, 1, 1),
            end_date_period=date(2024, 1, 31),
        )
        assert r.treatment_uuid == uid

    def test_automated_report_create(self):
        uid = uuid4()
        r = AutomatedReportCreate(
            treatment_uuid=uid,
            issue_date=date(2024, 1, 1),
            start_date_period=date(2024, 1, 1),
            end_date_period=date(2024, 1, 31),
        )
        assert r.treatment_uuid == uid

    def test_treatment_report_update_partial(self):
        update = TreatmentReportUpdate(analysis="new analysis")
        data = update.model_dump(exclude_unset=True)
        assert data == {"analysis": "new analysis"}


class TestPatientWithTreatmentSchemas:
    def test_patient_with_treatment_create(self):
        schema = PatientWithTreatmentCreate(
            patient_schema=PatientCreate(
                first_name="John", last_name="Doe"
            ),
            treatment_schema=TreatmentCreate(
                weekday=Weekdays.MONDAY,
                start_time=time(9, 0),
                end_time=time(10, 0),
            ),
        )
        assert schema.patient_schema.first_name == "John"
        assert schema.treatment_schema.weekday == Weekdays.MONDAY

    def test_patient_with_treatment_update(self):
        schema = PatientWithTreatmentUpdate(
            patient_schema=PatientUpdate(first_name="Jane"),
            treatment_schema=TreatmentUpdate(weekday=Weekdays.FRIDAY),
        )
        assert schema.patient_schema.first_name == "Jane"


class TestTokenSchemas:
    def test_token(self):
        t = Token(access_token="abc123", token_type="bearer")
        assert t.access_token == "abc123"

    def test_token_payload(self):
        tp = TokenPayload(sub="user-uuid", type="access")
        assert tp.sub == "user-uuid"

    def test_token_csrf(self):
        tc = TokenCSRF(csrf_token="sometoken")
        assert tc.csrf_token == "sometoken"


class TestMessageSchemas:
    def test_message(self):
        m = Message(message="ok")
        assert m.message == "ok"

    def test_details(self):
        d = Details(detail="some detail")
        assert d.detail == "some detail"
