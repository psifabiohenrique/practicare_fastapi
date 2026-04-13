import io
import pytest
import zipfile
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.export_service import ExportService

@pytest.mark.asyncio
async def test_generate_user_backup_success(mock_db, mock_treatment, mock_record, mock_report):
    user_uuid = "user-123"
    
    # Mock treatments
    with patch("src.services.export_service.PatientWithTreatmentService.get_treatments_with_user_uuid", new_callable=AsyncMock) as mock_get_treatments:
        mock_get_treatments.return_value = [mock_treatment]
        
        # Mock records result
        mock_records_result = MagicMock()
        mock_records_result.scalars.return_value.all.return_value = [mock_record]
        
        # Mock reports result
        mock_reports_result = MagicMock()
        mock_reports_result.scalars.return_value.all.return_value = [mock_report]
        
        mock_db.execute.side_effect = [mock_records_result, mock_reports_result]
        
        result = await ExportService.generate_user_backup(mock_db, user_uuid)
        
        assert isinstance(result, io.BytesIO)
        
        # Verify ZIP content
        with zipfile.ZipFile(result, "r") as zip_file:
            file_list = zip_file.namelist()
            assert any("Prontuários.md" in name for name in file_list)
            assert any("Relatórios.md" in name for name in file_list)

@pytest.mark.asyncio
async def test_generate_user_backup_empty(mock_db):
    user_uuid = "user-123"
    with patch("src.services.export_service.PatientWithTreatmentService.get_treatments_with_user_uuid", new_callable=AsyncMock) as mock_get_treatments:
        mock_get_treatments.return_value = []
        result = await ExportService.generate_user_backup(mock_db, user_uuid)
        assert isinstance(result, io.BytesIO)
        with zipfile.ZipFile(result, "r") as zip_file:
            assert len(zip_file.namelist()) == 0

@pytest.mark.asyncio
async def test_generate_user_backup_no_records_no_reports(mock_db, mock_treatment):
    user_uuid = "user-123"
    with patch("src.services.export_service.PatientWithTreatmentService.get_treatments_with_user_uuid", new_callable=AsyncMock) as mock_get_treatments:
        mock_get_treatments.return_value = [mock_treatment]
        
        mock_records_result = MagicMock()
        mock_records_result.scalars.return_value.all.return_value = []
        
        mock_reports_result = MagicMock()
        mock_reports_result.scalars.return_value.all.return_value = []
        
        mock_db.execute.side_effect = [mock_records_result, mock_reports_result]
        
        result = await ExportService.generate_user_backup(mock_db, user_uuid)
        with zipfile.ZipFile(result, "r") as zip_file:
            assert "John Doe/info.txt" in zip_file.namelist()
