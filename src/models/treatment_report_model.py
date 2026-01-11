import uuid
from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class TreatmentReport(Base):
    __tablename__ = "treatment_reports"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(
        String, default=lambda: str(uuid.uuid4()), unique=True, index=True
    )
    treatment_uuid = Column(String, ForeignKey("treatments.uuid"))

    demand_description = Column(String, nullable=True)
    procedures = Column(String, nullable=True)
    analysis = Column(String, nullable=True)
    conclusion = Column(String, nullable=True)

    issue_date = Column(Date)
    start_date_period = Column(Date)
    end_date_period = Column(Date)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )

    treatment = relationship("Treatment", back_populates="treatment_reports")
