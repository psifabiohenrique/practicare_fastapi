import uuid
from datetime import date, datetime

from pydantic import BaseModel

from src.models.usage_statistic import ProcessType


class UsageStatisticCreate(BaseModel):
    user_uuid: uuid.UUID
    job_uuid: uuid.UUID | None = None
    process_type: ProcessType
    input_tokens: int = 0
    output_tokens: int = 0
    audio_duration_seconds: float | None = None
    audio_duration_after_vad_seconds: float | None = None


class UsageStatisticRead(BaseModel):
    uuid: uuid.UUID
    user_uuid: uuid.UUID
    job_uuid: uuid.UUID | None = None
    process_type: ProcessType
    input_tokens: int
    output_tokens: int
    audio_duration_seconds: float | None = None
    audio_duration_after_vad_seconds: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DashboardResponse(BaseModel):
    # Token usage
    total_input_tokens: int = 0
    total_output_tokens: int = 0

    # Audio durations (in seconds)
    total_audio_duration: float = 0.0
    total_audio_duration_after_vad: float = 0.0

    # Process counts (from usage_statistics in period)
    total_transcriptions: int = 0
    total_records_generated: int = 0
    total_reports_generated: int = 0

    # Entity counts (overall, not period-filtered)
    active_treatments_count: int = 0

    # Entity counts (period-filtered)
    records_count: int = 0
    reports_count: int = 0

    # Period
    start_date: date
    end_date: date
