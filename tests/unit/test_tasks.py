from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.ai.ai_result import AIResult
from src.ai.exceptions import AIFatalError, AITransientError
from src.models.automated_record_job import JobStatus
from src.models.automated_report_job import ReportJobStatus
from src.tasks.record_generation import (
    comunicate_record_fail,
    do_generate_record,
    do_transcribe_audio,
    generate_record,
    generate_record_logic,
    transcribe_audio,
    transcribe_audio_logic,
)
from src.tasks.report_generation import (
    comunicate_report_fail,
    do_generate_report,
    generate_report_logic,
    generate_report_task,
)


@pytest.fixture
def job_uuid():
    return uuid4()


class TestRecordGenerationTasks:
    @pytest.mark.asyncio
    @patch("src.tasks.record_generation.get_async_session")
    @patch("src.tasks.record_generation.AutomatedRecordService")
    @patch("src.tasks.record_generation.TreatmentRecordService")
    async def test_comunicate_record_fail(
        self, mock_trs, mock_ars, mock_gas, mock_db, job_uuid
    ):
        mock_gas.return_value = mock_db
        mock_job = MagicMock()
        mock_job.treatment_record_uuid = uuid4()
        mock_job.user_uuid = str(uuid4())
        mock_ars.get_job = AsyncMock(return_value=mock_job)
        mock_trs.update_treatment_record = AsyncMock()

        await comunicate_record_fail(job_uuid, "error message")

        mock_trs.update_treatment_record.assert_called_once()
        mock_db.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.tasks.record_generation.get_async_session")
    @patch("src.tasks.record_generation.AutomatedRecordService")
    @patch("src.tasks.record_generation.generate_record")
    async def test_transcribe_audio_logic_success(
        self, mock_gen_rec_task, mock_ars, mock_gas, mock_db, job_uuid
    ):
        mock_gas.return_value = mock_db
        mock_ars.generate_transcription = AsyncMock(
            return_value=AIResult(
                content="transcription result",
                input_tokens=10,
                output_tokens=10,
            )
        )
        mock_ars.update_job_status = AsyncMock()

        await transcribe_audio_logic(job_uuid, "test.wav")

        mock_ars.update_job_status.assert_any_call(
            db=mock_db, job_uuid=job_uuid, status=JobStatus.TRANSCRIBING
        )
        mock_gen_rec_task.delay.assert_called_once_with(job_uuid=job_uuid)
        mock_db.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.tasks.record_generation.get_async_session")
    @patch("src.tasks.record_generation.AutomatedRecordService")
    async def test_transcribe_audio_logic_empty_result(
        self, mock_ars, mock_gas, mock_db, job_uuid
    ):
        mock_gas.return_value = mock_db
        mock_ars.update_job_status = AsyncMock()
        mock_ars.generate_transcription = AsyncMock(
            return_value=AIResult(content="", input_tokens=0, output_tokens=0)
        )

        with pytest.raises(AITransientError):
            await transcribe_audio_logic(job_uuid, "test.wav")

    @pytest.mark.asyncio
    @patch("src.tasks.record_generation.get_async_session")
    @patch("src.tasks.record_generation.AutomatedRecordService")
    @patch("src.tasks.record_generation.TreatmentRecordService")
    async def test_generate_record_logic_success(
        self, mock_trs, mock_ars, mock_gas, mock_db, job_uuid
    ):
        mock_gas.return_value = mock_db
        mock_job = MagicMock()
        mock_job.treatment_record_uuid = uuid4()
        mock_job.treatment_uuid = str(uuid4())
        mock_job.user_uuid = str(uuid4())
        mock_job.transcription = "some transcription"
        mock_ars.get_job = AsyncMock(return_value=mock_job)
        mock_ars.generate_record = AsyncMock(
            return_value=AIResult(
                content="record content", input_tokens=50, output_tokens=50
            )
        )
        mock_ars.update_job_status = AsyncMock()
        mock_trs.update_treatment_record = AsyncMock()

        await generate_record_logic(job_uuid)

        mock_trs.update_treatment_record.assert_called_once()
        mock_db.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.tasks.record_generation.get_async_session")
    @patch("src.tasks.record_generation.AutomatedRecordService")
    async def test_generate_record_logic_invalid_format(
        self, mock_ars, mock_gas, mock_db, job_uuid
    ):
        mock_gas.return_value = mock_db
        mock_job = MagicMock()
        mock_ars.get_job = AsyncMock(return_value=mock_job)
        mock_ars.generate_record = AsyncMock(return_value=None)
        mock_ars.update_job_status = AsyncMock()

        with pytest.raises(
            AITransientError,
            match="Registro de prontuário em formato indevido.",
        ):
            await generate_record_logic(job_uuid)

    @patch("src.tasks.record_generation.transcribe_audio_logic")
    @patch("src.tasks.record_generation.comunicate_record_fail")
    def test_do_transcribe_audio_wrappers(
        self, mock_fail, mock_logic, job_uuid
    ):
        # Success
        mock_logic.return_value = None
        do_transcribe_audio(job_uuid, "test.wav")

        # Transient
        mock_logic.side_effect = AITransientError("transient")
        mock_fail.return_value = MagicMock()
        with pytest.raises(AITransientError):
            do_transcribe_audio(job_uuid, "test.wav")

        # Fatal
        mock_logic.side_effect = AIFatalError("fatal")
        with pytest.raises(AIFatalError):
            do_transcribe_audio(job_uuid, "test.wav")

        # Unexpected
        mock_logic.side_effect = Exception("Unexpected")
        with pytest.raises(Exception, match="Unexpected"):
            do_transcribe_audio(job_uuid, "test.wav")

    @patch("src.tasks.record_generation.generate_record_logic")
    @patch("src.tasks.record_generation.comunicate_record_fail")
    def test_do_generate_record_wrappers(
        self, mock_fail, mock_logic, job_uuid
    ):
        # Success
        mock_logic.return_value = None
        do_generate_record(job_uuid)

        # Transient
        mock_logic.side_effect = AITransientError("transient")
        mock_fail.return_value = MagicMock()
        with pytest.raises(AITransientError):
            do_generate_record(job_uuid)

        # Fatal
        mock_logic.side_effect = AIFatalError("fatal")
        with pytest.raises(AIFatalError):
            do_generate_record(job_uuid)

        # Unexpected
        mock_logic.side_effect = Exception("Unexpected")
        with pytest.raises(Exception, match="Unexpected"):
            do_generate_record(job_uuid)

    @patch("src.tasks.record_generation.do_transcribe_audio")
    def test_celery_transcribe_audio_call(self, mock_do):
        transcribe_audio.run(uuid4(), "test.wav")
        mock_do.assert_called_once()

    @patch("src.tasks.record_generation.do_generate_record")
    @patch("src.tasks.record_generation.current_task")
    def test_celery_generate_record_call(self, mock_current, mock_do):
        mock_current.request.retries = 3
        job_id = uuid4()
        generate_record.run(job_id)
        mock_do.assert_called_once_with(job_id, 3)


class TestReportGenerationTasks:
    @pytest.mark.asyncio
    @patch("src.tasks.report_generation.get_async_session")
    @patch("src.tasks.report_generation.AutomatedReportService")
    @patch("src.tasks.report_generation.TreatmentReportService")
    async def test_comunicate_report_fail(
        self, mock_trs, mock_ars, mock_gas, mock_db, job_uuid
    ):
        mock_gas.return_value = mock_db
        mock_job = MagicMock()
        mock_job.treatment_report_uuid = uuid4()
        mock_job.user_uuid = str(uuid4())
        mock_ars.get_job = AsyncMock(return_value=mock_job)
        mock_trs.update_treatment_report = AsyncMock()

        await comunicate_report_fail(job_uuid, "error message")

        mock_trs.update_treatment_report.assert_called_once()
        mock_db.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.tasks.report_generation.get_async_session")
    @patch("src.tasks.report_generation.AutomatedReportService")
    async def test_generate_report_logic_success(
        self, mock_ars, mock_gas, mock_db, job_uuid
    ):
        mock_gas.return_value = mock_db
        mock_job = MagicMock()
        mock_ars.get_job = AsyncMock(return_value=mock_job)
        mock_ars.update_job_status = AsyncMock()
        mock_ars.generate_report_content = AsyncMock()

        await generate_report_logic(job_uuid)

        mock_ars.update_job_status.assert_called_once_with(
            db=mock_db,
            job_uuid=job_uuid,
            status=ReportJobStatus.GENERATING_REPORT,
        )
        mock_db.close.assert_called_once()

    @patch("src.tasks.report_generation.generate_report_logic")
    @patch("src.tasks.report_generation.comunicate_report_fail")
    def test_do_generate_report_wrappers(
        self, mock_fail, mock_logic, job_uuid
    ):
        # Success
        mock_logic.return_value = None
        do_generate_report(job_uuid)

        # Transient
        mock_logic.side_effect = AITransientError("transient")
        mock_fail.return_value = MagicMock()
        with pytest.raises(AITransientError):
            do_generate_report(job_uuid)

        # Fatal
        mock_logic.side_effect = AIFatalError("fatal")
        with pytest.raises(AIFatalError):
            do_generate_report(job_uuid)

        # Unexpected
        mock_logic.side_effect = Exception("Unexpected")
        with pytest.raises(Exception, match="Unexpected"):
            do_generate_report(job_uuid)

    @patch("src.tasks.report_generation.do_generate_report")
    def test_celery_generate_report_task_call(self, mock_do):
        generate_report_task.run(uuid4())
        mock_do.assert_called_once()
