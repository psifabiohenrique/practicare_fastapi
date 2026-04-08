import uuid as uuid_pkg
from datetime import datetime

from sqlalchemy import UUID as SQLUUID
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from src.database import Base


class TreatmentContext(Base):
    __tablename__ = "treatment_contexts"

    uuid = Column(
        SQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid_pkg.uuid4,
        index=True,
    )
    treatment_uuid = Column(
        SQLUUID,
        ForeignKey("treatments.uuid"),
        unique=True,
        nullable=False,
    )

    life_dynamics = Column(Text, nullable=True)
    clinical_history = Column(Text, nullable=True)
    psychological_patterns = Column(Text, nullable=True)
    therapeutic_goals = Column(Text, nullable=True)
    medication_notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )
    is_update_scheduled = Column(Boolean, default=False, nullable=False)

    treatment = relationship("Treatment", back_populates="treatment_context")
    drafts = relationship(
        "TreatmentContextDraft",
        back_populates="treatment_context",
    )


class TreatmentContextDraft(Base):
    __tablename__ = "treatment_context_drafts"

    uuid = Column(
        SQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid_pkg.uuid4,
        index=True,
    )
    treatment_context_uuid = Column(
        SQLUUID,
        ForeignKey("treatment_contexts.uuid"),
        nullable=False,
    )
    treatment_record_uuid = Column(
        SQLUUID,
        ForeignKey("treatment_records.uuid"),
        nullable=False,
    )

    life_dynamics = Column(Text, nullable=True)
    clinical_history = Column(Text, nullable=True)
    psychological_patterns = Column(Text, nullable=True)
    therapeutic_goals = Column(Text, nullable=True)
    medication_notes = Column(Text, nullable=True)

    is_applied = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.now)

    treatment_context = relationship(
        "TreatmentContext", back_populates="drafts"
    )
    treatment_record = relationship("TreatmentRecord")
