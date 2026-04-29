import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from fastapi import Request
from src.routers.treatment_report_controller import delete_treatment_report

@pytest.mark.asyncio
async def test_delete_treatment_report_endpoint(mock_db, mock_user):
    with patch("src.routers.treatment_report_controller.TreatmentReportService.delete_treatment_report", new_callable=AsyncMock) as mock_service:
        request = MagicMock(spec=Request)
        await delete_treatment_report(request, uuid4(), mock_db, mock_user)
        mock_service.assert_called_once()
