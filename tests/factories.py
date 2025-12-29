import uuid as uuid_pkg

import factory

from models import User


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
