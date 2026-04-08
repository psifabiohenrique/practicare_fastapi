from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TreatmentContextRead(BaseModel):
    uuid: UUID
    treatment_uuid: UUID
    life_dynamics: str | None = None
    clinical_history: str | None = None
    psychological_patterns: str | None = None
    therapeutic_goals: str | None = None
    medication_notes: str | None = None
    is_update_scheduled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TreatmentContextUpdate(BaseModel):
    life_dynamics: str | None = None
    clinical_history: str | None = None
    psychological_patterns: str | None = None
    therapeutic_goals: str | None = None
    medication_notes: str | None = None


class TreatmentContextDraftRead(BaseModel):
    uuid: UUID
    treatment_context_uuid: UUID
    treatment_record_uuid: UUID
    life_dynamics: str | None = None
    clinical_history: str | None = None
    psychological_patterns: str | None = None
    therapeutic_goals: str | None = None
    medication_notes: str | None = None
    is_applied: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TreatmentContextWithDraftRead(BaseModel):
    context: TreatmentContextRead | None = None
    pending_draft: TreatmentContextDraftRead | None = None


class TreatmentContextApplyDraft(BaseModel):
    life_dynamics: str | None = None
    clinical_history: str | None = None
    psychological_patterns: str | None = None
    therapeutic_goals: str | None = None
    medication_notes: str | None = None


class TreatmentContextGenerate(BaseModel):
    historical_notes: str | None = None
    include_existing_records: bool = False
