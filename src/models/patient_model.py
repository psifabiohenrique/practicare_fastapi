import uuid as uuid_pkg
from enum import Enum

from sqlalchemy import Column, Date, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from src.database import Base


class Gender(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
    OTHERS = "Others"


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(
        String, default=lambda: str(uuid_pkg.uuid4()), unique=True, index=True
    )
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    birth_date = Column(Date, nullable=True)
    gender = Column(SQLEnum(Gender), nullable=True)

    @hybrid_property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    treatments = relationship("Treatment", back_populates="patient")
