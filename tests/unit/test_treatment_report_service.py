from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.core.exceptions import ForbiddenError, NotFoundError
from src.models import TreatmentReport
from src.services.treatment_report_service import TreatmentReportService


@pytest.fixture
def mock_db():
    return AsyncMock()


class TestGetTreatmentReport:
    @pytest.mark.asyncio
    async def test_not_found(self, mock_db):
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = result_mock

        with pytest.raises(
            NotFoundError, match="Treatment report not found"
        ):
            await TreatmentReportService.get_treatment_report(
                mock_db, uuid4(), str(uuid4())
            )

    @pytest.mark.asyncio
    async def test_forbidden(self, mock_db):
        user_uuid = str(uuid4())
        other_user_uuid = str(uuid4())

        mock_treatment = MagicMock()
        mock_treatment.user_uuid = other_user_uuid

        mock_report = MagicMock(spec=TreatmentReport)
        mock_report.treatment = mock_treatment

        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = mock_report
        mock_db.execute.return_value = result_mock

        with pytest.raises(
            ForbiddenError, match="Access denied"
        ):
            await TreatmentReportService.get_treatment_report(
                mock_db, uuid4(), user_uuid
            )

    @pytest.mark.asyncio
    async def test_success(self, mock_db):
        user_uuid = str(uuid4())

        mock_treatment = MagicMock()
        mock_treatment.user_uuid = user_uuid

        mock_report = MagicMock(spec=TreatmentReport)
        mock_report.treatment = mock_treatment

        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = mock_report
        mock_db.execute.return_value = result_mock

        result = await TreatmentReportService.get_treatment_report(
            mock_db, uuid4(), user_uuid
        )
        assert result == mock_report
