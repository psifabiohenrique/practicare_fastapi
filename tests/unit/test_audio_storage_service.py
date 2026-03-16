from unittest.mock import AsyncMock, patch

import pytest

from src.services.audio_storage_service import AudioStorageService


@pytest.fixture
def mock_upload_file():
    mock_file = AsyncMock()
    mock_file.filename = "test_audio.webm"
    mock_file.read.return_value = b"fake audio content"
    return mock_file


@pytest.mark.asyncio
async def test_save_upload_success(mock_upload_file):
    with patch("src.services.audio_storage_service.AsyncOpenAI") as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.files.create = AsyncMock()
        mock_instance.files.create.return_value.id = "file-123"

        file_id = await AudioStorageService.save_upload(mock_upload_file)

        assert file_id == "file-123"
        mock_instance.files.create.assert_called_once()
        # Verify the filename passed to OpenAI has the correct extension
        args, kwargs = mock_instance.files.create.call_args
        filename, content = kwargs["file"]
        assert filename.endswith(".webm")
        assert content == b"fake audio content"


@pytest.mark.asyncio
async def test_save_upload_no_extension(mock_upload_file):
    mock_upload_file.filename = "test_audio"
    with patch("src.services.audio_storage_service.AsyncOpenAI") as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.files.create = AsyncMock()
        mock_instance.files.create.return_value.id = "file-456"

        file_id = await AudioStorageService.save_upload(mock_upload_file)

        assert file_id == "file-456"
        args, kwargs = mock_instance.files.create.call_args
        filename, _ = kwargs["file"]
        assert filename.endswith(".webm")  # Default extension


@pytest.mark.asyncio
async def test_save_upload_error(mock_upload_file):
    with patch("src.services.audio_storage_service.AsyncOpenAI") as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.files.create = AsyncMock(
            side_effect=Exception("OpenAI error")
        )

        with pytest.raises(Exception, match="OpenAI error"):
            await AudioStorageService.save_upload(mock_upload_file)


@pytest.mark.asyncio
async def test_get_file_content_success():
    with patch("src.services.audio_storage_service.AsyncOpenAI") as MockClient:
        mock_instance = MockClient.return_value
        mock_response = AsyncMock()
        mock_response.read.return_value = b"downloaded content"
        mock_instance.files.content = AsyncMock(return_value=mock_response)

        content = await AudioStorageService.get_file_content("file-123")

        assert content == b"downloaded content"
        mock_instance.files.content.assert_called_once_with("file-123")


@pytest.mark.asyncio
async def test_get_file_content_error():
    with patch("src.services.audio_storage_service.AsyncOpenAI") as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.files.content = AsyncMock(
            side_effect=Exception("Download error")
        )

        with pytest.raises(Exception, match="Download error"):
            await AudioStorageService.get_file_content("file-123")


@pytest.mark.asyncio
async def test_delete_file_success():
    with patch("src.services.audio_storage_service.AsyncOpenAI") as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.files.delete = AsyncMock()

        await AudioStorageService.delete_file("file-123")

        mock_instance.files.delete.assert_called_once_with("file-123")


@pytest.mark.asyncio
async def test_delete_file_warning_non_critical():
    with patch("src.services.audio_storage_service.AsyncOpenAI") as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.files.delete = AsyncMock(
            side_effect=Exception("Delete error")
        )

        # Should NOT raise exception based on service implementation
        # (uses warning and pass)
        await AudioStorageService.delete_file("file-123")
        mock_instance.files.delete.assert_called_once_with("file-123")
