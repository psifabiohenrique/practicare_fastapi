import uuid as uuid_pkg
from enum import Enum

from sqlalchemy import UUID as SQLUUID
from sqlalchemy import Column, ForeignKey, Time
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from src.database import Base


class Weekdays(str, Enum):
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"
    SATURDAY = "Saturday"
    SUNDAY = "Sunday"


class Treatment(Base):
    __tablename__ = "treatments"

    uuid = Column(
        SQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid_pkg.uuid4,
        index=True,
    )

    user_uuid = Column(SQLUUID, ForeignKey("users.uuid"))
    patient_uuid = Column(SQLUUID, ForeignKey("patients.uuid"))
    weekday = Column(
        SQLEnum(Weekdays), default=Weekdays.MONDAY, nullable=False
    )
    start_time = Column(Time)
    end_time = Column(Time)

    user = relationship("User", back_populates="treatments")
    patient = relationship("Patient", back_populates="treatments")
    treatment_records = relationship(
        "TreatmentRecord", back_populates="treatment"
    )
    treatment_reports = relationship(
        "TreatmentReport", back_populates="treatment"
    )
