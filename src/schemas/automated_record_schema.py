from pydantic import BaseModel

# class AutomatedRecordJobBase(BaseModel):
#     user_uuid: str
#     treatment_record_uuid: str
#     audio_path: str
#     status: str
#     error_message: str | None = None
#     transcription: str | None = None
#     generated_record: str | None = None
#     created_at: datetime
#     updated_at: datetime


class JobResponse(BaseModel):
    job_uuid: str
    status: str
