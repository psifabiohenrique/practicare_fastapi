from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.audio_storage_service import AudioStorageService


class TestAudioStorageService:
    @pytest.mark.asyncio
    @patch("src.services.audio_storage_service.AsyncOpenAI")
    @patch("src.services.audio_storage_service.settings")
    async def test_save_upload(self, mock_settings, MockOpenAI):
        mock_settings.OPENAI_API_KEY = "test-key"

        # Mock OpenAI response
        client_instance = MockOpenAI.return_value
        client_instance.files.create = AsyncMock()
        mock_response = MagicMock()
        mock_response.id = "file-123"
        client_instance.files.create.return_value = mock_response

        # Mock UploadFile
        mock_upload = AsyncMock()
        mock_upload.read.return_value = b"audio content"
        mock_upload.filename = "audio.webm"

        file_id = await AudioStorageService.save_upload(mock_upload)

        assert file_id == "file-123"
        client_instance.files.create.assert_called_once()
        # Verify purpose and filename suffix handling
        args, kwargs = client_instance.files.create.call_args
        assert kwargs["purpose"] == "assistants"
        assert kwargs["file"][0].endswith(".webm")

    @pytest.mark.asyncio
    @patch("src.services.audio_storage_service.AsyncOpenAI")
    @patch("src.services.audio_storage_service.settings")
    async def test_get_file_content(self, mock_settings, MockOpenAI):
        mock_settings.OPENAI_API_KEY = "test-key"

        client_instance = MockOpenAI.return_value
        client_instance.files.content = AsyncMock()
        mock_response = AsyncMock()
        mock_response.read.return_value = b"file content"
        client_instance.files.content.return_value = mock_response

        content = await AudioStorageService.get_file_content("file-123")

        assert content == b"file content"
        client_instance.files.content.assert_called_once_with("file-123")

    @pytest.mark.asyncio
    @patch("src.services.audio_storage_service.AsyncOpenAI")
    @patch("src.services.audio_storage_service.settings")
    async def test_delete_file_success(self, mock_settings, MockOpenAI):
        mock_settings.OPENAI_API_KEY = "test-key"

        client_instance = MockOpenAI.return_value
        client_instance.files.delete = AsyncMock()

        await AudioStorageService.delete_file("file-123")

        client_instance.files.delete.assert_called_once_with("file-123")

    @pytest.mark.asyncio
    @patch("src.services.audio_storage_service.AsyncOpenAI")
    @patch("src.services.audio_storage_service.settings")
    async def test_delete_file_failure_non_critical(
        self, mock_settings, MockOpenAI
    ):
        mock_settings.OPENAI_API_KEY = "test-key"

        client_instance = MockOpenAI.return_value
        client_instance.files.delete = AsyncMock(
            side_effect=Exception("Delete failed")
        )

        # Should not raise
        await AudioStorageService.delete_file("file-123")

        client_instance.files.delete.assert_called_once_with("file-123")

    @pytest.mark.asyncio
    @patch("src.services.audio_storage_service.AsyncOpenAI")
    @patch("src.services.audio_storage_service.settings")
    async def test_save_upload_failure(self, mock_settings, MockOpenAI):
        mock_settings.OPENAI_API_KEY = "test-key"
        client_instance = MockOpenAI.return_value
        client_instance.files.create = AsyncMock(
            side_effect=Exception("API Error")
        )

        mock_upload = AsyncMock()
        mock_upload.read.return_value = b"content"
        mock_upload.filename = "audio.webm"

        with pytest.raises(Exception, match="API Error"):
            await AudioStorageService.save_upload(mock_upload)

    @pytest.mark.asyncio
    @patch("src.services.audio_storage_service.AsyncOpenAI")
    @patch("src.services.audio_storage_service.settings")
    async def test_get_file_content_failure(self, mock_settings, MockOpenAI):
        mock_settings.OPENAI_API_KEY = "test-key"
        client_instance = MockOpenAI.return_value
        client_instance.files.content = AsyncMock(
            side_effect=Exception("API Error")
        )

        with pytest.raises(Exception, match="API Error"):
            await AudioStorageService.get_file_content("file-123")
