import datetime
import uuid as uuid_pkg

import factory

from src.models import (
    Gender,
    Patient,
    Treatment,
    TreatmentRecord,
    TreatmentReport,
    User,
)
from src.models.auth_session_model import AuthSession


class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session = None  # Will be set in conftest.py
        sqlalchemy_session_persistence = None

    uuid = factory.LazyFunction(lambda: str(uuid_pkg.uuid4()))
    name = factory.Faker("name")
    email = factory.Faker("email")
    hashed_password = factory.LazyFunction(
        lambda: "hashed_password"
    )  # Mocked for tests


class PatientFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Patient
        sqlalchemy_session = None
        sqlalchemy_session_persistence = None

    uuid = factory.LazyFunction(lambda: str(uuid_pkg.uuid4()))
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.Faker("email")
    phone = factory.Faker("phone_number")
    gender = factory.Iterator([Gender.MALE, Gender.FEMALE, Gender.OTHERS])


class TreatmentFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Treatment
        sqlalchemy_session = None
        sqlalchemy_session_persistence = None

    uuid = factory.LazyFunction(lambda: str(uuid_pkg.uuid4()))
    user = factory.SubFactory(UserFactory)
    user_uuid = factory.SelfAttribute("user.uuid")
    patient = factory.SubFactory(PatientFactory)
    patient_uuid = factory.SelfAttribute("patient.uuid")
    weekday = "Monday"
    start_time = datetime.time(9, 0)
    end_time = datetime.time(10, 0)


class TreatmentRecordFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = TreatmentRecord
        sqlalchemy_session = None
        sqlalchemy_session_persistence = None

    uuid = factory.LazyFunction(lambda: str(uuid_pkg.uuid4()))
    treatment = factory.SubFactory(TreatmentFactory)
    treatment_uuid = factory.SelfAttribute("treatment.uuid")

    status = "ready"
    date = factory.Faker("date_object")
    start_time = datetime.time(9, 0)
    end_time = datetime.time(10, 0)
    content = factory.Faker("paragraph")
    record_number = factory.Sequence(lambda n: n + 1)


class TreatmentReportFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = TreatmentReport
        sqlalchemy_session = None
        sqlalchemy_session_persistence = None

    uuid = factory.LazyFunction(lambda: str(uuid_pkg.uuid4()))
    treatment = factory.SubFactory(TreatmentFactory)
    treatment_uuid = factory.SelfAttribute("treatment.uuid")

    demand_description = factory.Faker("paragraph")
    procedures = factory.Faker("paragraph")
    analysis = factory.Faker("paragraph")
    conclusion = factory.Faker("paragraph")

    issue_date = factory.Faker("date_object")
    start_date_period = factory.Faker("date_object")
    end_date_period = factory.Faker("date_object")


class AuthSessionFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = AuthSession
        sqlalchemy_session = None
        sqlalchemy_session_persistence = None

    uuid = factory.LazyFunction(uuid_pkg.uuid4)
    user_uuid = factory.LazyFunction(uuid_pkg.uuid4)
    expires_at = factory.LazyFunction(
        lambda: (
            datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(hours=2)
        )
    )
    last_accessed_at = factory.LazyFunction(
        lambda: datetime.datetime.now(datetime.timezone.utc)
    )
