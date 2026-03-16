from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

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
    job.uuid = str(uuid4())
    job.user_uuid = str(uuid4())
    job.treatment_uuid = str(uuid4())
    job.treatment_record_uuid = str(uuid4())
    job.status = JobStatus.PENDING
    job.audio_path = "test.webm"
    return job


class TestAutomatedRecordServiceJobLifecycle:
    @pytest.mark.asyncio
    async def test_create_job(self, mock_db):
        t_uuid = uuid4()
        tr_uuid = uuid4()
        u_uuid = str(uuid4())

        job = await AutomatedRecordService.create_job(
            mock_db,
            t_uuid,
            tr_uuid,
            u_uuid,
            "audio.webm",
        )

        assert isinstance(job, AutomatedRecordJob)
        assert job.user_uuid == u_uuid
        assert job.treatment_uuid == str(t_uuid)
        assert job.treatment_record_uuid == str(tr_uuid)
        assert job.audio_path == "audio.webm"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_job_success(self, mock_db, mock_job):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_job
        mock_db.execute.return_value = result_mock

        job = await AutomatedRecordService.get_job(
            mock_db, UUID(mock_job.uuid)
        )

        assert job == mock_job
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, mock_db):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        with pytest.raises(NotFoundError, match="Job not found"):
            await AutomatedRecordService.get_job(mock_db, uuid4())

    @pytest.mark.asyncio
    async def test_update_job_status(self, mock_db, mock_job):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_job
        mock_db.execute.return_value = result_mock

        updated_job = await AutomatedRecordService.update_job_status(
            mock_db,
            UUID(mock_job.uuid),
            JobStatus.COMPLETED,
            transcription="Transcribed text",
        )

        assert updated_job.status == JobStatus.COMPLETED
        assert updated_job.transcription == "Transcribed text"
        mock_db.commit.assert_called_once()


class TestAutomatedRecordServiceProcessing:
    @pytest.mark.asyncio
    @patch("src.services.automated_record_service.convert_to_wav")
    @patch("src.services.automated_record_service.split_by_vad")
    async def test_upload_audio_file_success(
        self,
        mock_split,
        mock_convert,
        mock_db,
        mock_job,
    ):
        with (
            patch("os.path.exists", return_value=True),
            patch("os.remove") as mock_remove,
            patch(
                "src.services.automated_record_service.TranscriptionChain"
            ) as MockTC,
        ):
            mock_instance = MockTC.return_value
            mock_instance.upload_audio = AsyncMock()
            mock_instance.upload_audio.return_value.name = "remote.wav"

            # Setup get_job within upload_audio_file
            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = mock_job
            mock_db.execute.return_value = result_mock

            result = await AutomatedRecordService.upload_audio_file(
                mock_db, UUID(mock_job.uuid), "local.webm"
            )

            assert result.name == "remote.wav"
            mock_convert.assert_called_once()
            mock_split.assert_called_once()
            mock_instance.upload_audio.assert_called_once()
            assert mock_remove.call_count >= 1

    @pytest.mark.asyncio
    @patch("src.services.automated_record_service.convert_to_wav")
    @patch("src.services.automated_record_service.split_by_vad")
    async def test_upload_audio_file_failure(
        self,
        mock_split,
        mock_convert,
        mock_db,
        mock_job,
    ):
        with (
            patch("os.path.exists", return_value=True),
            patch("os.remove"),
            patch(
                "src.services.automated_record_service."
                "TreatmentRecordService.update_treatment_record"
            ) as mock_update_record,
            patch("src.services.automated_record_service.TranscriptionChain"),
        ):
            mock_convert.side_effect = Exception("FFmpeg error")

            # Setup get_job within upload_audio_file
            mock_job.treatment_record_uuid = str(uuid4())
            mock_job.user_uuid = str(uuid4())
            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = mock_job
            mock_db.execute.return_value = result_mock

            # Service handles exception and doesn't re-raise
            await AutomatedRecordService.upload_audio_file(
                mock_db, UUID(mock_job.uuid), "local.webm"
            )

            assert mock_job.status == JobStatus.FAILED
            assert mock_job.error_message == "FFmpeg error"
            mock_update_record.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.services.automated_record_service.convert_to_wav")
    @patch("src.services.automated_record_service.split_by_vad")
    async def test_upload_audio_file_no_remote_name(
        self,
        mock_split,
        mock_convert,
        mock_db,
        mock_job,
    ):
        with (
            patch("os.path.exists", return_value=True),
            patch("os.remove"),
            patch(
                "src.services.automated_record_service.TranscriptionChain"
            ) as MockTC,
        ):
            mock_instance = MockTC.return_value
            mock_instance.upload_audio = AsyncMock()
            mock_instance.upload_audio.return_value.name = None  # Missing name

            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = mock_job
            mock_db.execute.return_value = result_mock

            await AutomatedRecordService.upload_audio_file(
                mock_db, UUID(mock_job.uuid), "local.webm"
            )

            assert mock_job.status == JobStatus.FAILED
            assert "Audio file name is missing" in mock_job.error_message

    @pytest.mark.asyncio
    @patch("src.services.automated_record_service.convert_to_wav")
    @patch("src.services.automated_record_service.split_by_vad")
    async def test_upload_audio_file_cleanup_error_suppressed(
        self,
        mock_split,
        mock_convert,
        mock_db,
        mock_job,
    ):
        with (
            patch("os.path.exists", return_value=True),
            patch("os.remove"),
            patch(
                "src.services.automated_record_service."
                "TreatmentRecordService.update_treatment_record",
                side_effect=Exception("Cleanup fail"),
            ) as mock_update_record,
            patch("src.services.automated_record_service.TranscriptionChain"),
        ):
            mock_convert.side_effect = Exception("FFmpeg error")

            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = mock_job
            mock_db.execute.return_value = result_mock

            # Should not raise even if update_treatment_record fails
            await AutomatedRecordService.upload_audio_file(
                mock_db, UUID(mock_job.uuid), "local.webm"
            )

            assert mock_job.status == JobStatus.FAILED
            mock_update_record.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.services.automated_record_service.TranscriptionChain")
    async def test_generate_transcription(self, MockTranscriptionChain):
        mock_instance = MockTranscriptionChain.return_value
        mock_instance.transcribe = AsyncMock(return_value="Valid text")

        result = await AutomatedRecordService.generate_transcription(
            AsyncMock(), "file.wav", uuid4()
        )

        assert result == "Valid text"
        mock_instance.transcribe.assert_called_once_with("file.wav")

    @pytest.mark.asyncio
    @patch("src.services.automated_record_service.RecordGenerationChain")
    async def test_generate_record_success(
        self, MockRecordChain, mock_db, mock_job
    ):
        with (
            patch(
                "src.services.automated_record_service."
                "TreatmentReportService.get_treatment_reports",
                return_value=[],
            ),
            patch(
                "src.services.automated_record_service."
                "PatientWithTreatmentService.get_patient_with_treatment_uuid"
            ) as mock_get_patient,
        ):
            mock_patient = MagicMock()
            mock_patient.gender = "M"
            mock_get_patient.return_value = mock_patient

            mock_instance = MockRecordChain.return_value
            mock_instance.generate = AsyncMock(return_value="Record text")

            result = await AutomatedRecordService.generate_record(
                mock_db, "Transcription", mock_job
            )

            assert result == "Record text"
            mock_instance.generate.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.services.automated_record_service.RecordGenerationChain")
    async def test_generate_record_failure(
        self, MockRecordChain, mock_db, mock_job
    ):
        with (
            patch(
                "src.services.automated_record_service."
                "TreatmentReportService.get_treatment_reports",
                return_value=[],
            ),
            patch(
                "src.services.automated_record_service."
                "PatientWithTreatmentService.get_patient_with_treatment_uuid"
            ) as mock_get_patient,
        ):
            mock_patient = MagicMock()
            mock_patient.gender = "F"
            mock_get_patient.return_value = mock_patient

            mock_instance = MockRecordChain.return_value
            mock_instance.generate = AsyncMock(
                side_effect=Exception("Gen error")
            )

            result = await AutomatedRecordService.generate_record(
                mock_db, "Transcription", mock_job
            )

            assert result is None  # Fails gracefully based on code
            mock_instance.generate.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.services.automated_record_service.RecordGenerationChain")
    async def test_generate_record_with_reports(
        self, MockRecordChain, mock_db, mock_job
    ):
        mock_report = MagicMock()
        mock_report.demand_description = "Demanda"
        mock_report.procedures = "Procedimentos"
        mock_report.analysis = "Análise"
        mock_report.conclusion = "Conclusão"

        with (
            patch(
                "src.services.automated_record_service."
                "TreatmentReportService.get_treatment_reports",
                return_value=[mock_report],
            ),
            patch(
                "src.services.automated_record_service."
                "PatientWithTreatmentService.get_patient_with_treatment_uuid"
            ) as mock_get_patient,
        ):
            mock_patient = MagicMock()
            mock_patient.gender = "F"
            mock_get_patient.return_value = mock_patient

            mock_instance = MockRecordChain.return_value
            mock_instance.generate = AsyncMock(
                return_value="Record with context"
            )

            result = await AutomatedRecordService.generate_record(
                mock_db, "Transcription", mock_job
            )

            assert result == "Record with context"
            _, kwargs = mock_instance.generate.call_args
            assert "Demanda" in kwargs["context"]
