from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.models import (
    Patient,
    Treatment,
    TreatmentRecord,
    TreatmentReport,
    User,
)
from src.models.treatment_context_model import (
    TreatmentContext,
    TreatmentContextDraft,
)


@pytest.fixture
def mock_db():
    db = AsyncMock()
    # Common methods
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    db.delete = AsyncMock()
    db.close = AsyncMock()
    return db


@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.uuid = "user-123"
    user.email = "test@example.com"
    user.name = "Test User"
    user.hashed_password = "hashed_password"
    return user


@pytest.fixture
def mock_patient():
    patient = MagicMock(spec=Patient)
    patient.uuid = uuid4()
    patient.first_name = "John"
    patient.last_name = "Doe"
    patient.full_name = "John Doe"
    patient.phone = "+5511999999999"
    patient.gender = "M"
    return patient


@pytest.fixture
def mock_treatment(mock_patient):
    treatment = MagicMock(spec=Treatment)
    treatment.uuid = uuid4()
    treatment.user_uuid = "user-123"
    treatment.patient_uuid = mock_patient.uuid
    treatment.patient = mock_patient
    treatment.status = "ACTIVE"
    return treatment


@pytest.fixture
def mock_record(mock_treatment):
    from datetime import date
    record = MagicMock(spec=TreatmentRecord)
    record.uuid = uuid4()
    record.treatment_uuid = mock_treatment.uuid
    record.record_number = 1
    record.content = "Record content"
    record.type = "session"
    record.date = date(2023, 1, 1)
    record.treatment = mock_treatment
    return record


@pytest.fixture
def mock_report(mock_treatment):
    report = MagicMock(spec=TreatmentReport)
    report.uuid = uuid4()
    report.treatment_uuid = mock_treatment.uuid
    report.content = "Report content"
    report.treatment = mock_treatment
    return report


@pytest.fixture
def mock_context(mock_treatment):
    context = MagicMock(spec=TreatmentContext)
    context.uuid = uuid4()
    context.treatment_uuid = str(mock_treatment.uuid)
    context.life_dynamics = None
    context.clinical_history = None
    context.psychological_patterns = None
    context.therapeutic_goals = None
    context.medication_notes = None
    context.is_update_scheduled = False
    return context


@pytest.fixture
def mock_draft(mock_context, mock_record):
    draft = MagicMock(spec=TreatmentContextDraft)
    draft.uuid = uuid4()
    draft.treatment_context_uuid = str(mock_context.uuid)
    draft.treatment_record_uuid = str(mock_record.uuid)
    draft.life_dynamics = None
    draft.clinical_history = None
    draft.psychological_patterns = None
    draft.therapeutic_goals = None
    draft.medication_notes = None
    draft.is_applied = False
    return draft
