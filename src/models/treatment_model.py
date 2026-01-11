import uuid
from enum import Enum

from sqlalchemy import Column, ForeignKey, Integer, String, Time
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from database import Base


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
    treatment_records = relationship(
        "TreatmentRecord", back_populates="treatment"
    )
    treatment_reports = relationship(
        "TreatmentReport", back_populates="treatment"
    )
