import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Time,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from database import Base
from utils.enums import Gender, Weekdays


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(
        String, default=lambda: str(uuid.uuid4()), unique=True, index=True
    )
    name = Column(String)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )

    treatments = relationship("Treatment", back_populates="user")


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(
        String, default=lambda: str(uuid.uuid4()), unique=True, index=True
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


class Treatment(Base):
    __tablename__ = "treatments"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(
        String, default=lambda: str(uuid.uuid4()), unique=True, index=True
    )
    user_uuid = Column(String, ForeignKey("users.uuid"))
    patient_uuid = Column(String, ForeignKey("patients.uuid"))
    weekday = Column(
        SQLEnum(Weekdays), default=Weekdays.MONDAY, nullable=False
    )
    start_time = Column(Time)
    end_time = Column(Time)

    user = relationship("User", back_populates="treatments")
    patient = relationship("Patient", back_populates="treatments")
