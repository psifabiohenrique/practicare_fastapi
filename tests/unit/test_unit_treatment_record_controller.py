import os
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import Request

from src.models.treatment_record_model import RecordStatus
from src.routers.treatment_record_controller import (
    process_audio_upload_background,
)
from src.schemas.treatment_record_schema import InternalTreatmentRecordUpdate


@pytest.fixture
def mock_session_local(mock_db):
    with patch(
        "src.routers.treatment_record_controller.SessionLocal"
    ) as mock:
        # Simulate async context manager
        mock.return_value.__aenter__.return_value = mock_db
        mock.return_value.__aexit__ = AsyncMock(return_value=None)
        yield mock


@pytest.fixture
def mock_automated_service():
    with patch(
        "src.routers.treatment_record_controller.AutomatedRecordService"
    ) as mock:
        mock.upload_audio_file = AsyncMock()
        mock.get_job = AsyncMock()
        yield mock


@pytest.fixture
def mock_transcribe_task():
    with patch(
        "src.routers.treatment_record_controller.transcribe_audio"
    ) as mock:
        yield mock


@pytest.fixture
def mock_treatment_service():
    with patch(
        "src.routers.treatment_record_controller.TreatmentRecordService"
    ) as mock:
        mock.update_treatment_record = AsyncMock()
        yield mock


@pytest.fixture
def mock_sleep():
    with patch(
        "src.routers.treatment_record_controller.asyncio.sleep",
        new_callable=AsyncMock,
    ) as mock:
        yield mock


@pytest.fixture
def mock_os_path_exists():
    with patch("src.routers.treatment_record_controller.os.path.exists") as mock:
        yield mock


@pytest.fixture
def mock_os_remove():
    with patch("src.routers.treatment_record_controller.os.remove") as mock:
        yield mock


@pytest.fixture
def mock_logger():
    with patch("src.routers.treatment_record_controller.logger") as mock:
        yield mock


@pytest.mark.asyncio
async def test_process_audio_upload_background_success(
    mock_session_local,
    mock_automated_service,
    mock_transcribe_task,
    mock_os_path_exists,
    mock_os_remove,
    mock_db,
):
    # Setup
    job_uuid = uuid4()
    audio_path = "test.webm"
    uploaded_audio = MagicMock()
    uploaded_audio.name = "remote.wav"
    mock_automated_service.upload_audio_file.return_value = uploaded_audio
    mock_os_path_exists.return_value = True

    # Execute
    await process_audio_upload_background(job_uuid, audio_path)

    # Verify
    mock_automated_service.upload_audio_file.assert_called_once_with(
        db=mock_db, job_uuid=job_uuid, audio_path=audio_path
    )
    mock_transcribe_task.apply_async.assert_called_once_with(
        kwargs={
            "job_uuid": job_uuid,
            "file_name": "remote.wav",
        },
        countdown=30,
    )
    mock_os_remove.assert_called_once_with(audio_path)


@pytest.mark.asyncio
async def test_process_audio_upload_background_retry_success(
    mock_session_local,
    mock_automated_service,
    mock_transcribe_task,
    mock_sleep,
    mock_os_path_exists,
    mock_os_remove,
    mock_db,
):
    # Setup
    job_uuid = uuid4()
    audio_path = "test.webm"
    uploaded_audio = MagicMock()
    uploaded_audio.name = "remote.wav"

    # Fail first time, succeed second time
    mock_automated_service.upload_audio_file.side_effect = [
        Exception("Upload error"),
        uploaded_audio,
    ]
    mock_os_path_exists.return_value = True

    # Execute
    await process_audio_upload_background(job_uuid, audio_path)

    # Verify
    assert mock_automated_service.upload_audio_file.call_count == 2
    mock_transcribe_task.apply_async.assert_called_once()
    mock_sleep.assert_called_once_with(5)
    mock_os_remove.assert_called_once_with(audio_path)


@pytest.mark.asyncio
async def test_process_audio_upload_background_final_failure(
    mock_session_local,
    mock_automated_service,
    mock_transcribe_task,
    mock_sleep,
    mock_treatment_service,
    mock_os_path_exists,
    mock_os_remove,
    mock_db,
):
    # Setup
    job_uuid = uuid4()
    audio_path = "test.webm"
    mock_automated_service.upload_audio_file.side_effect = Exception(
        "Upload permanent error"
    )

    mock_job = MagicMock()
    mock_job.treatment_record_uuid = str(uuid4())
    mock_job.user_uuid = "user-123"
    mock_automated_service.get_job.return_value = mock_job

    mock_os_path_exists.return_value = True

    # Execute
    await process_audio_upload_background(job_uuid, audio_path)

    # Verify
    assert mock_automated_service.upload_audio_file.call_count == 2
    assert mock_transcribe_task.apply_async.call_count == 0
    assert mock_sleep.call_count == 1  # 2nd failure doesn't sleep
    mock_treatment_service.update_treatment_record.assert_called_once()

    # Check update call details
    args, kwargs = mock_treatment_service.update_treatment_record.call_args
    assert args[1] == UUID(mock_job.treatment_record_uuid)
    assert args[2] == mock_job.user_uuid
    update_schema = args[3]
    assert isinstance(update_schema, InternalTreatmentRecordUpdate)
    assert update_schema.status == RecordStatus.FAILED
    assert "Houve um erro" in update_schema.content

    mock_os_remove.assert_called_once_with(audio_path)


@pytest.mark.asyncio
async def test_process_audio_upload_background_final_failure_update_error(
    mock_session_local,
    mock_automated_service,
    mock_treatment_service,
    mock_logger,
    mock_os_path_exists,
    mock_os_remove,
    mock_db,
):
    # Setup
    job_uuid = uuid4()
    audio_path = "test.webm"
    mock_automated_service.upload_audio_file.side_effect = Exception("Fail")
    mock_automated_service.get_job.return_value = MagicMock(
        treatment_record_uuid=str(uuid4()), user_uuid="u"
    )

    # Fail the record update too
    mock_treatment_service.update_treatment_record.side_effect = Exception(
        "Update error"
    )
    mock_os_path_exists.return_value = True

    # Execute
    await process_audio_upload_background(job_uuid, audio_path)

    # Verifylogger.error was called
    mock_logger.error.assert_called()
    assert "Erro ao atualizar prontuário" in mock_logger.error.call_args[0][0]
    mock_os_remove.assert_called_once_with(audio_path)


@pytest.mark.asyncio
async def test_process_audio_upload_background_cleanup_error(
    mock_session_local,
    mock_automated_service,
    mock_os_path_exists,
    mock_os_remove,
    mock_logger,
    mock_db,
):
    # Setup
    job_uuid = uuid4()
    audio_path = "test.webm"
    mock_automated_service.upload_audio_file.return_value = MagicMock()
    mock_os_path_exists.return_value = True

    # Fail cleanup
    mock_os_remove.side_effect = Exception("Cleanup error")

    # Execute
    await process_audio_upload_background(job_uuid, audio_path)

    # Verify logger.warning was called for cleanup failure
    mock_logger.warning.assert_called()
    # Find the cleanup failure message
    warning_calls = [c[0][0] for c in mock_logger.warning.call_args_list]
    assert any("Falha ao deletar arquivo temporário" in msg for msg in warning_calls)

from src.routers.treatment_record_controller import delete_treatment_record

@pytest.mark.asyncio
async def test_delete_treatment_record_endpoint(mock_db, mock_user):
    with patch("src.routers.treatment_record_controller.TreatmentRecordService.delete_treatment_record", new_callable=AsyncMock) as mock_service:
        request = MagicMock(spec=Request)
        await delete_treatment_record(request, uuid4(), mock_db, mock_user)
        mock_service.assert_called_once()
