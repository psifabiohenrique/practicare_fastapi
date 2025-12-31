import datetime
import uuid as uuid_pkg

import factory

from models import Patient, Treatment, User


class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session = None  # Will be set in conftest.py
        sqlalchemy_session_persistence = "commit"

    id = factory.Sequence(lambda n: n)
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
        sqlalchemy_session_persistence = "commit"

    id = factory.Sequence(lambda n: n)
    uuid = factory.LazyFunction(lambda: str(uuid_pkg.uuid4()))
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.Faker("email")
    phone = factory.Faker("phone_number")


class TreatmentFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Treatment
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    id = factory.Sequence(lambda n: n)
    uuid = factory.LazyFunction(lambda: str(uuid_pkg.uuid4()))
    user = factory.SubFactory(UserFactory)
    user_uuid = factory.SelfAttribute("user.uuid")
    patient = factory.SubFactory(PatientFactory)
    patient_uuid = factory.SelfAttribute("patient.uuid")
    weekday = "Monday"
    start_time = datetime.time(9, 0)
    end_time = datetime.time(10, 0)
