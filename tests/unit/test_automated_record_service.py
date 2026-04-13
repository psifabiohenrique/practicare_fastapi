from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.ai.ai_result import AIResult
from src.core.exceptions import NotFoundError
from src.models.automated_record_job import AutomatedRecordJob, JobStatus
from src.services.automated_record_service import AutomatedRecordService
from src.utils.audio_processor import VADResult


@pytest.fixture
def mock_job():
    job = MagicMock(spec=AutomatedRecordJob)
    job.uuid = uuid4()
    job.user_uuid = uuid4()
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
        user_uuid = uuid4()

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

    @pytest.mark.asyncio
    @patch("src.services.automated_record_service.TreatmentService")
    @patch("src.services.automated_record_service.TreatmentRecordService")
    @patch(
        "src.services.automated_record_service.AutomatedRecordService.create_job",
        new_callable=AsyncMock,
    )
    async def test_initialize_job_new(
        self,
        mock_create_job,
        mock_record_service,
        mock_treatment_service,
        mock_db,
    ):
        mock_treatment_service.get_treatment_by_uuid = AsyncMock(
            return_value=MagicMock(start_time="10:00", end_time="11:00")
        )
        mock_record_service.create_treatment_record = AsyncMock(
            return_value=MagicMock(uuid=uuid4(), treatment_uuid=uuid4())
        )
        mock_create_job.return_value = MagicMock(uuid=uuid4())

        record, job = await AutomatedRecordService.initialize_job(
            mock_db,
            uuid4(),
            treatment_uuid=uuid4(),
            session_date="2024-01-01",
        )

        assert record is not None
        assert job is not None
        mock_treatment_service.get_treatment_by_uuid.assert_called_once()
        mock_record_service.create_treatment_record.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.services.automated_record_service.TreatmentRecordService")
    @patch(
        "src.services.automated_record_service.AutomatedRecordService.create_job",
        new_callable=AsyncMock,
    )
    async def test_initialize_job_reload(
        self, mock_create_job, mock_record_service, mock_db
    ):
        mock_record_service.get_treatment_record = AsyncMock(
            return_value=MagicMock(uuid=uuid4(), treatment_uuid=uuid4())
        )
        mock_create_job.return_value = MagicMock(uuid=uuid4())

        record, job = await AutomatedRecordService.initialize_job(
            mock_db, uuid4(), treatment_record_uuid=uuid4()
        )

        assert record is not None
        assert job is not None
        mock_record_service.get_treatment_record.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.services.automated_record_service.tempfile.gettempdir")
    @patch("pathlib.Path.mkdir")
    async def test_prepare_chunk_dir(self, mock_mkdir, mock_gettemp):
        mock_gettemp.return_value = "/tmp"
        job_uuid = uuid4()
        path = await AutomatedRecordService.prepare_chunk_dir(job_uuid)
        assert str(path) == f"/tmp/chunks_{job_uuid}"

    @pytest.mark.asyncio
    @patch(
        "src.services.automated_record_service.AutomatedRecordService.prepare_chunk_dir"
    )
    @patch("builtins.open", new_callable=MagicMock)
    async def test_save_audio_chunk(self, mock_open, mock_prepare):
        mock_prepare.return_value = MagicMock()
        await AutomatedRecordService.save_audio_chunk(uuid4(), 0, b"data")
        mock_open.assert_called_once()

    @pytest.mark.asyncio
    @patch(
        "src.services.automated_record_service.AutomatedRecordService.prepare_chunk_dir"
    )
    @patch("shutil.rmtree")
    @patch("shutil.copyfileobj")
    @patch("builtins.open", new_callable=MagicMock)
    @patch("src.services.automated_record_service.tempfile.gettempdir")
    async def test_finalize_chunked_upload_success(  # noqa: PLR0917
        self,
        mock_gettemp,
        mock_open,
        mock_copy,
        mock_rmtree,
        mock_prepare,
        mock_db,
    ):
        job_uuid = uuid4()
        chunk_dir = MagicMock()
        mock_prepare.return_value = chunk_dir
        chunk_dir.glob.return_value = [
            Path("chunk_00000"),
            Path("chunk_00001"),
        ]
        mock_gettemp.return_value = "/tmp"

        result = await AutomatedRecordService.finalize_chunked_upload(
            mock_db, job_uuid, 2
        )

        assert result == f"/tmp/audio_{job_uuid}.webm"
        assert mock_copy.call_count == 2
        mock_rmtree.assert_called_once_with(chunk_dir)

    @pytest.mark.asyncio
    @patch(
        "src.services.automated_record_service.AutomatedRecordService.prepare_chunk_dir"
    )
    async def test_finalize_chunked_upload_missing_chunks(
        self, mock_prepare, mock_db
    ):
        job_uuid = uuid4()
        chunk_dir = MagicMock()
        mock_prepare.return_value = chunk_dir
        chunk_dir.glob.return_value = [Path("chunk_00000")]

        with pytest.raises(ValueError, match="Missing chunks"):
            await AutomatedRecordService.finalize_chunked_upload(
                mock_db, job_uuid, 2
            )


class TestAutomatedRecordServiceProcessing:
    @pytest.mark.asyncio
    @patch("src.services.automated_record_service.UsageStatisticService")
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
    async def test_upload_audio_file_success(
        self,
        mock_remove,
        mock_exists,
        MockChain,
        mock_split,
        mock_convert,
        mock_update_status,
        mock_get_job,
        mock_usage_service,
        mock_db,
        mock_job,
    ):
        mock_get_job.return_value = mock_job
        mock_usage_service.create_statistic = AsyncMock()
        mock_exists.return_value = True
        mock_split.return_value = VADResult(
            output_path="path_vad.wav",
            original_duration_seconds=10.0,
            vad_duration_seconds=8.0,
        )

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
        assert mock_remove.call_count == 2
        assert mock_job.audio_duration_seconds == 10.0
        assert mock_job.audio_duration_after_vad_seconds == 8.0

    @pytest.mark.asyncio
    @patch("src.services.automated_record_service.UsageStatisticService")
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
        mock_usage_service,
        mock_db,
        mock_job,
    ):
        mock_get_job.return_value = mock_job
        mock_exists.return_value = False
        mock_split.return_value = VADResult(
            output_path="path_vad.wav",
            original_duration_seconds=10.0,
            vad_duration_seconds=8.0,
        )

        chain_instance = MockChain.return_value
        chain_instance.upload_audio = AsyncMock()
        audio_file = MagicMock()
        audio_file.name = None
        chain_instance.upload_audio.return_value = audio_file

        # Function now re-raises exceptions
        with pytest.raises(NotFoundError):
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
    @patch("src.services.automated_record_service.UsageStatisticService")
    @patch(
        "src.services.automated_record_service.AutomatedRecordService.get_job"
    )
    @patch("src.services.automated_record_service.TranscriptionChain")
    async def test_generate_transcription(
        self, MockChain, mock_get_job, mock_usage_service, mock_db, mock_job
    ):
        mock_get_job.return_value = mock_job
        mock_usage_service.create_statistic = AsyncMock()
        chain_instance = MockChain.return_value
        chain_instance.transcribe = AsyncMock()
        chain_instance.transcribe.return_value = AIResult(
            content="Transcribed text", input_tokens=100, output_tokens=200
        )

        result = await AutomatedRecordService.generate_transcription(
            mock_db, "file.wav", mock_job.uuid
        )

        assert isinstance(result, AIResult)
        assert result.content == "Transcribed text"
        chain_instance.transcribe.assert_called_once_with("file.wav")
        mock_usage_service.create_statistic.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.services.automated_record_service.UsageStatisticService")
    @patch(
        "src.services.automated_record_service.PatientWithTreatmentService.get_patient_with_treatment_uuid"
    )
    @patch("src.services.automated_record_service.RecordGenerationChain")
    async def test_generate_record(  # noqa: PLR0917
        self,
        MockChain,
        mock_get_patient,
        mock_usage_service,
        mock_db,
        mock_job,
    ):
        # Mock TreatmentContext query
        ctx_mock = MagicMock()
        ctx_mock.life_dynamics = "Life info"
        ctx_mock.clinical_history = None
        ctx_mock.psychological_patterns = None
        ctx_mock.therapeutic_goals = None
        ctx_mock.medication_notes = None

        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = ctx_mock
        mock_db.execute.return_value = result_mock

        # Mock patient
        patient = MagicMock()
        patient.gender = "Male"
        mock_get_patient.return_value = patient

        # Mock UsageStatisticService
        mock_usage_service.create_statistic = AsyncMock()

        # Mock Chain
        chain_instance = MockChain.return_value
        chain_instance.generate = AsyncMock()
        chain_instance.generate.return_value = AIResult(
            content="Generated Record", input_tokens=300, output_tokens=400
        )

        result = await AutomatedRecordService.generate_record(
            mock_db, "transcription", mock_job
        )

        assert result.content == "Generated Record"
        chain_instance.generate.assert_called_once()
        mock_usage_service.create_statistic.assert_called_once()
        args, kwargs = chain_instance.generate.call_args
        assert kwargs["gender"] == "Male"
        assert "Life info" in kwargs["context"]

    @pytest.mark.asyncio
    @patch("src.services.automated_record_service.UsageStatisticService")
    @patch(
        "src.services.automated_record_service.PatientWithTreatmentService.get_patient_with_treatment_uuid"
    )
    @patch("src.services.automated_record_service.RecordGenerationChain")
    async def test_generate_record_no_context(  # noqa: PLR0917
        self,
        MockChain,
        mock_get_patient,
        mock_usage_service,
        mock_db,
        mock_job,
    ):
        # Mock TreatmentContext missing
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = result_mock

        patient = MagicMock()
        patient.gender = "Female"
        mock_get_patient.return_value = patient

        mock_usage_service.create_statistic = AsyncMock()

        chain_instance = MockChain.return_value
        chain_instance.generate = AsyncMock()
        chain_instance.generate.return_value = AIResult(
            content="Generated", input_tokens=10, output_tokens=10
        )

        await AutomatedRecordService.generate_record(
            mock_db, "trans", mock_job
        )

        args, kwargs = chain_instance.generate.call_args
        assert kwargs["context"] == ""

    @pytest.mark.asyncio
    @patch("src.services.automated_record_service.UsageStatisticService")
    @patch(
        "src.services.automated_record_service.PatientWithTreatmentService.get_patient_with_treatment_uuid"
    )
    @patch("src.services.automated_record_service.RecordGenerationChain")
    async def test_generate_record_full_context(  # noqa: PLR0917
        self,
        MockChain,
        mock_get_patient,
        mock_usage_service,
        mock_db,
        mock_job,
    ):
        ctx_mock = MagicMock()
        ctx_mock.life_dynamics = "D"
        ctx_mock.clinical_history = "H"
        ctx_mock.psychological_patterns = "P"
        ctx_mock.therapeutic_goals = "G"
        ctx_mock.medication_notes = "M"

        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = ctx_mock
        mock_db.execute.return_value = result_mock

        mock_get_patient.return_value = MagicMock(gender="Male")
        mock_usage_service.create_statistic = AsyncMock()
        chain_instance = MockChain.return_value
        chain_instance.generate = AsyncMock(return_value=AIResult(content="R", input_tokens=1, output_tokens=1))

        await AutomatedRecordService.generate_record(mock_db, "T", mock_job)
        
        _, kwargs = chain_instance.generate.call_args
        assert "Dinâmicas de Vida: D" in kwargs["context"]
        assert "Histórico Clínico: H" in kwargs["context"]
        assert "Padrões Psicológicos: P" in kwargs["context"]
        assert "Objetivos Terapêuticos: G" in kwargs["context"]
        assert "Medicações: M" in kwargs["context"]

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

        # Function now re-raises exceptions
        with pytest.raises(Exception, match="Conv error"):
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
    @patch("src.services.automated_record_service.UsageStatisticService")
    @patch(
        "src.services.automated_record_service.PatientWithTreatmentService.get_patient_with_treatment_uuid"
    )
    @patch("src.services.automated_record_service.RecordGenerationChain")
    async def test_generate_record_chain_failure(  # noqa: PLR0917
        self,
        MockChain,
        mock_get_patient,
        mock_usage_service,
        mock_db,
        mock_job,
    ):
        # Mock TreatmentContext missing
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = result_mock

        mock_get_patient.return_value = MagicMock(gender="Other")
        chain_instance = MockChain.return_value
        chain_instance.generate = AsyncMock(side_effect=Exception("AI error"))

        result = await AutomatedRecordService.generate_record(
            mock_db, "trans", mock_job
        )

        assert result is None

    @pytest.mark.asyncio
    @patch("src.services.automated_record_service.logger")
    @patch("src.services.automated_record_service.UsageStatisticService")
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
    async def test_upload_audio_file_cleanup_failure(  # noqa: PLR0917
        self,
        mock_remove,
        mock_exists,
        MockChain,
        mock_split,
        mock_convert,
        mock_update_status,
        mock_get_job,
        mock_usage_service,
        mock_logger,
        mock_db,
        mock_job,
    ):
        mock_get_job.return_value = mock_job
        mock_exists.return_value = True
        mock_split.return_value = VADResult(
            output_path="path_vad.wav",
            original_duration_seconds=10.0,
            vad_duration_seconds=8.0,
        )

        chain_instance = MockChain.return_value
        chain_instance.upload_audio = AsyncMock()
        audio_file = MagicMock()
        audio_file.name = "remote_path.wav"
        chain_instance.upload_audio.return_value = audio_file

        # Trigger exception in cleanup
        mock_remove.side_effect = Exception("Cleanup error")

        # The function should still complete (or re-raise if it failed before finally,
        # but here it succeeds before finally)
        result = await AutomatedRecordService.upload_audio_file(
            mock_db, mock_job.uuid, "test.webm"
        )

        assert result == audio_file
        mock_logger.warning.assert_called_with(
            "Falha ao limpar arquivos temporários de áudio: %s",
            mock_remove.side_effect,
        )
