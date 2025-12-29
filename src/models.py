import uuid

from sqlalchemy import Column, Integer, String

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(
        String, default=lambda: str(uuid.uuid4()), unique=True, index=True
    )
    name = Column(String)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
