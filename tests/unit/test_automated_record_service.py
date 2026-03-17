from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.core.exceptions import NotFoundError
from src.models.automated_record_job import AutomatedRecordJob, JobStatus
from src.services.automated_record_service import AutomatedRecordService


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_job():
    job = MagicMock(spec=AutomatedRecordJob)
    job.uuid = uuid4()
    job.user_uuid = "user-123"
    job.treatment_uuid = str(uuid4())
    job.treatment_record_uuid = str(uuid4())
    job.status = JobStatus.PENDING
    job.audio_path = "original.webm"
    job.transcription = None
    job.error_message = None
    return job


class TestAutomatedRecordServiceLifecycle:
    @pytest.mark.asyncio
    async def test_create_job(self, mock_db):
        treatment_uuid = uuid4()
        record_uuid = uuid4()
        user_uuid = "user-123"

        job = await AutomatedRecordService.create_job(
            mock_db, treatment_uuid, record_uuid, user_uuid, "path/to/audio"
        )

        assert isinstance(job, AutomatedRecordJob)
        assert job.status == JobStatus.PENDING
        assert job.audio_path == "path/to/audio"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_job_success(self, mock_db, mock_job):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_job
        mock_db.execute.return_value = result_mock

        job = await AutomatedRecordService.get_job(mock_db, mock_job.uuid)
        assert job == mock_job

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, mock_db):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        with pytest.raises(NotFoundError, match="Job not found"):
            await AutomatedRecordService.get_job(mock_db, uuid4())

    @pytest.mark.asyncio
    @patch(
        "src.services.automated_record_service.AutomatedRecordService.get_job"
    )
    async def test_update_job_status(self, mock_get_job, mock_db, mock_job):
        mock_get_job.return_value = mock_job

        await AutomatedRecordService.update_job_status(
            mock_db,
            mock_job.uuid,
            JobStatus.COMPLETED,
            transcription="Hello",
            error_message="Error",
            audio_path="new_path.wav",
        )

        assert mock_job.status == JobStatus.COMPLETED
        assert mock_job.transcription == "Hello"
        assert mock_job.error_message == "Error"
        assert mock_job.audio_path == "new_path.wav"
        mock_db.commit.assert_called_once()


class TestAutomatedRecordServiceProcessing:
    @pytest.mark.asyncio
    @patch(
        "src.services.automated_record_service.AutomatedRecordService.get_job"
    )
    @patch(
        "src.services.automated_record_service.AutomatedRecordService.update_job_status"
    )
    @patch("src.services.automated_record_service.convert_to_wav")
    @patch("src.services.automated_record_service.split_by_vad")
    @patch("src.services.automated_record_service.TranscriptionChain")
    @patch("os.path.exists")
    @patch("os.remove")
    async def test_upload_audio_file_success(  # noqa: PLR0917
        self,
        mock_remove,
        mock_exists,
        MockChain,
        mock_split,
        mock_convert,
        mock_update_status,
        mock_get_job,
        mock_db,
        mock_job,
    ):
        mock_get_job.return_value = mock_job
        mock_exists.return_value = True

        chain_instance = MockChain.return_value
        chain_instance.upload_audio = AsyncMock()
        audio_file = MagicMock()
        audio_file.name = "remote_path.wav"
        chain_instance.upload_audio.return_value = audio_file

        result = await AutomatedRecordService.upload_audio_file(
            mock_db, mock_job.uuid, "test.webm"
        )

        assert result == audio_file
        mock_convert.assert_called_once()
        mock_split.assert_called_once()
        assert mock_update_status.call_count == 2
        assert mock_remove.call_count == 3

    @pytest.mark.asyncio
    @patch(
        "src.services.automated_record_service.AutomatedRecordService.update_job_status"
    )
    @patch("src.services.automated_record_service.convert_to_wav")
    @patch("src.services.automated_record_service.split_by_vad")
    @patch("src.services.automated_record_service.TranscriptionChain")
    @patch(
        "src.services.automated_record_service.AutomatedRecordService.get_job"
    )
    @patch("os.path.exists")
    @patch("os.remove")
    async def test_upload_audio_file_missing_name(  # noqa: PLR0917
        self,
        mock_remove,
        mock_exists,
        mock_get_job,
        MockChain,
        mock_split,
        mock_convert,
        mock_update_status,
        mock_db,
        mock_job,
    ):
        mock_get_job.return_value = mock_job
        mock_exists.return_value = False

        chain_instance = MockChain.return_value
        chain_instance.upload_audio = AsyncMock()
        audio_file = MagicMock()
        audio_file.name = None
        chain_instance.upload_audio.return_value = audio_file

        # Function handles exception internally and doesn't re-raise
        await AutomatedRecordService.upload_audio_file(
            mock_db, mock_job.uuid, "test.webm"
        )

        mock_update_status.assert_any_call(
            mock_db,
            mock_job.uuid,
            JobStatus.FAILED,
            error_message="Audio file name is missing after upload.",
        )

    @pytest.mark.asyncio
    @patch("src.services.automated_record_service.TranscriptionChain")
    async def test_generate_transcription(self, MockChain, mock_db):
        chain_instance = MockChain.return_value
        chain_instance.transcribe = AsyncMock()
        chain_instance.transcribe.return_value = "Transcribed text"

        result = await AutomatedRecordService.generate_transcription(
            mock_db, "file.wav", uuid4()
        )

        assert result == "Transcribed text"
        chain_instance.transcribe.assert_called_once_with("file.wav")

    @pytest.mark.asyncio
    @patch(
        "src.services.automated_record_service.TreatmentReportService.get_treatment_reports"
    )
    @patch(
        "src.services.automated_record_service.PatientWithTreatmentService.get_patient_with_treatment_uuid"
    )
    @patch("src.services.automated_record_service.RecordGenerationChain")
    async def test_generate_record(
        self,
        MockChain,
        mock_get_patient,
        mock_get_reports,
        mock_db,
        mock_job,
    ):
        # Mock reports
        report = MagicMock()
        report.demand_description = "demand"
        report.procedures = "procs"
        report.analysis = "anal"
        report.conclusion = "conc"
        mock_get_reports.return_value = [report]

        # Mock patient
        patient = MagicMock()
        patient.gender = "Male"
        mock_get_patient.return_value = patient

        # Mock Chain
        chain_instance = MockChain.return_value
        chain_instance.generate = AsyncMock()
        chain_instance.generate.return_value = "Generated Record"

        result = await AutomatedRecordService.generate_record(
            mock_db, "transcription", mock_job
        )

        assert result == "Generated Record"
        chain_instance.generate.assert_called_once()
        args, kwargs = chain_instance.generate.call_args
        assert kwargs["gender"] == "Male"
        assert "demand" in kwargs["context"]

    @pytest.mark.asyncio
    @patch(
        "src.services.automated_record_service.TreatmentReportService.get_treatment_reports"
    )
    @patch(
        "src.services.automated_record_service.PatientWithTreatmentService.get_patient_with_treatment_uuid"
    )
    @patch("src.services.automated_record_service.RecordGenerationChain")
    async def test_generate_record_no_reports(
        self,
        MockChain,
        mock_get_patient,
        mock_get_reports,
        mock_db,
        mock_job,
    ):
        mock_get_reports.return_value = []
        patient = MagicMock()
        patient.gender = "Female"
        mock_get_patient.return_value = patient

        chain_instance = MockChain.return_value
        chain_instance.generate = AsyncMock()
        chain_instance.generate.return_value = "Generated"

        await AutomatedRecordService.generate_record(
            mock_db, "trans", mock_job
        )

        args, kwargs = chain_instance.generate.call_args
        assert "Nenhum relatório" in kwargs["context"]

    @pytest.mark.asyncio
    @patch(
        "src.services.automated_record_service.AutomatedRecordService.get_job"
    )
    @patch(
        "src.services.automated_record_service.AutomatedRecordService.update_job_status"
    )
    @patch("src.services.automated_record_service.convert_to_wav")
    @patch(
        "src.services.automated_record_service.TreatmentRecordService.update_treatment_record"
    )
    @patch("os.path.exists")
    @patch("os.remove")
    async def test_upload_audio_file_failure_with_record_update(  # noqa: PLR0917
        self,
        mock_remove,
        mock_exists,
        mock_update_record,
        mock_convert,
        mock_update_status,
        mock_get_job,
        mock_db,
        mock_job,
    ):
        mock_get_job.return_value = mock_job
        mock_exists.return_value = False
        mock_convert.side_effect = Exception("Conv error")

        # Mock TreatmentRecordService failure too to cover nested except
        mock_update_record.side_effect = Exception("Update fail")

        # Function handles exception internally and doesn't re-raise
        await AutomatedRecordService.upload_audio_file(
            mock_db, mock_job.uuid, "test.webm"
        )

        mock_update_record.assert_called_once()
        mock_update_status.assert_any_call(
            mock_db,
            mock_job.uuid,
            JobStatus.FAILED,
            error_message="Conv error",
        )

    @pytest.mark.asyncio
    @patch(
        "src.services.automated_record_service.TreatmentReportService.get_treatment_reports"
    )
    @patch(
        "src.services.automated_record_service.PatientWithTreatmentService.get_patient_with_treatment_uuid"
    )
    @patch("src.services.automated_record_service.RecordGenerationChain")
    async def test_generate_record_chain_failure(
        self,
        MockChain,
        mock_get_patient,
        mock_get_reports,
        mock_db,
        mock_job,
    ):
        mock_get_reports.return_value = []
        mock_get_patient.return_value = MagicMock(gender="Other")
        chain_instance = MockChain.return_value
        chain_instance.generate = AsyncMock(side_effect=Exception("AI error"))

        result = await AutomatedRecordService.generate_record(
            mock_db, "trans", mock_job
        )

        assert result is None
