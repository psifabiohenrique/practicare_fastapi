import uuid as uuid_pkg
from datetime import datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database import Base


class TreatmentRecord(Base):
    __tablename__ = "treatment_records"

    __table_args__ = (UniqueConstraint("treatment_uuid", "record_number"),)

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(
        String, default=lambda: str(uuid_pkg.uuid4()), unique=True, index=True
    )
    treatment_uuid = Column(String, ForeignKey("treatments.uuid"))

    date = Column(Date)
    start_time = Column(Time)
    end_time = Column(Time)
    content = Column(String)
    record_number = Column(Integer)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )

    treatment = relationship("Treatment", back_populates="treatment_records")
