import uuid as uuid_pkg
from datetime import datetime

from sqlalchemy import UUID as SQLUUID
from sqlalchemy import Boolean, Column, DateTime, ForeignKey
from sqlalchemy.orm import relationship

try:
    from sqlalchemy import JSON
except ImportError:  # pragma: no cover
    from sqlalchemy import Text as JSON

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

    # Each field stores a JSON list of bullet-point strings
    life_dynamics = Column(JSON, nullable=True)
    clinical_history = Column(JSON, nullable=True)
    psychological_patterns = Column(JSON, nullable=True)
    therapeutic_goals = Column(JSON, nullable=True)
    medication_notes = Column(JSON, nullable=True)
    techniques = Column(JSON, nullable=True)
    requested_activities = Column(JSON, nullable=True)

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

    # Each field stores a JSON dict: {"add": [...], "remove": [...]}
    life_dynamics = Column(JSON, nullable=True)
    clinical_history = Column(JSON, nullable=True)
    psychological_patterns = Column(JSON, nullable=True)
    therapeutic_goals = Column(JSON, nullable=True)
    medication_notes = Column(JSON, nullable=True)
    techniques = Column(JSON, nullable=True)
    requested_activities = Column(JSON, nullable=True)

    is_applied = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.now)

    treatment_context = relationship(
        "TreatmentContext", back_populates="drafts"
    )
    treatment_record = relationship("TreatmentRecord")
