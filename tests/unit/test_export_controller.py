import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from fastapi.responses import StreamingResponse
from src.routers.export_controller import download_backup

@pytest.mark.asyncio
@patch("src.routers.export_controller.ExportService.generate_user_backup")
async def test_download_backup(mock_service, mock_db, mock_user):
    mock_service.return_value = MagicMock()
    res = await download_backup(mock_db, mock_user)
    assert isinstance(res, StreamingResponse)
    assert "attachment; filename=backup_prontuarios_" in res.headers["Content-Disposition"]
