from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

ContextField = list[str] | None


class TreatmentContextRead(BaseModel):
    uuid: UUID
    treatment_uuid: UUID
    life_dynamics: ContextField = None
    clinical_history: ContextField = None
    psychological_patterns: ContextField = None
    therapeutic_goals: ContextField = None
    medication_notes: ContextField = None
    is_update_scheduled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TreatmentContextUpdate(BaseModel):
    life_dynamics: ContextField = None
    clinical_history: ContextField = None
    psychological_patterns: ContextField = None
    therapeutic_goals: ContextField = None
    medication_notes: ContextField = None


class ContextFieldDiff(BaseModel):
    """Structured diff suggested by the AI for a single context field."""

    add: list[str] = []
    remove: list[str] = []


class TreatmentContextDraftRead(BaseModel):
    uuid: UUID
    treatment_context_uuid: UUID
    treatment_record_uuid: UUID
    life_dynamics: ContextFieldDiff | None = None
    clinical_history: ContextFieldDiff | None = None
    psychological_patterns: ContextFieldDiff | None = None
    therapeutic_goals: ContextFieldDiff | None = None
    medication_notes: ContextFieldDiff | None = None
    is_applied: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TreatmentContextWithDraftRead(BaseModel):
    context: TreatmentContextRead | None = None
    pending_draft: TreatmentContextDraftRead | None = None


class TreatmentContextApplyDraft(BaseModel):
    """Final context state sent by the frontend after reviewing the draft."""

    life_dynamics: ContextField = None
    clinical_history: ContextField = None
    psychological_patterns: ContextField = None
    therapeutic_goals: ContextField = None
    medication_notes: ContextField = None


class TreatmentContextGenerate(BaseModel):
    historical_notes: str | None = None
    include_existing_records: bool = False
