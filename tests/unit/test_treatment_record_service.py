from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.core.exceptions import ForbiddenError, NotFoundError
from src.models import TreatmentRecord
from src.services.treatment_record_service import TreatmentRecordService


@pytest.fixture
def mock_db():
    return AsyncMock()


class TestGetTreatmentRecord:
    @pytest.mark.asyncio
    async def test_not_found(self, mock_db):
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = result_mock

        with pytest.raises(NotFoundError, match="Treatment record not found"):
            await TreatmentRecordService.get_treatment_record(
                mock_db, uuid4(), str(uuid4())
            )

    @pytest.mark.asyncio
    async def test_forbidden(self, mock_db):
        user_uuid = str(uuid4())
        other_user_uuid = str(uuid4())

        mock_treatment = MagicMock()
        mock_treatment.user_uuid = other_user_uuid

        mock_record = MagicMock(spec=TreatmentRecord)
        mock_record.treatment = mock_treatment

        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = mock_record
        mock_db.execute.return_value = result_mock

        with pytest.raises(ForbiddenError, match="Access denied"):
            await TreatmentRecordService.get_treatment_record(
                mock_db, uuid4(), user_uuid
            )

    @pytest.mark.asyncio
    async def test_success(self, mock_db):
        user_uuid = str(uuid4())

        mock_treatment = MagicMock()
        mock_treatment.user_uuid = user_uuid

        mock_record = MagicMock(spec=TreatmentRecord)
        mock_record.treatment = mock_treatment

        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = mock_record
        mock_db.execute.return_value = result_mock

        result = await TreatmentRecordService.get_treatment_record(
            mock_db, uuid4(), user_uuid
        )
        assert result == mock_record
