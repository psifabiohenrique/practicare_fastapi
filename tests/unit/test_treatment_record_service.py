from datetime import date, time
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.core.exceptions import ForbiddenError, NotFoundError
from src.models import Treatment, TreatmentRecord
from src.schemas.treatment_record_schema import (
    TreatmentRecordCreate,
    TreatmentRecordUpdate,
)
from src.services.treatment_record_service import TreatmentRecordService


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_treatment():
    treatment = MagicMock(spec=Treatment)
    treatment.uuid = uuid4()
    treatment.user_uuid = "user-123"
    return treatment


@pytest.fixture
def mock_record(mock_treatment):
    record = MagicMock(spec=TreatmentRecord)
    record.uuid = uuid4()
    record.treatment_uuid = mock_treatment.uuid
    record.record_number = 1
    record.content = "Record content"
    record.date = date(2023, 1, 1)
    record.treatment = mock_treatment
    return record


class TestTreatmentRecordServiceCRUD:
    @pytest.mark.asyncio
    async def test_get_treatment_record_success(self, mock_db, mock_record):
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = mock_record
        mock_db.execute.return_value = result_mock

        record = await TreatmentRecordService.get_treatment_record(
            mock_db, mock_record.uuid, "user-123"
        )

        assert record == mock_record

    @pytest.mark.asyncio
    async def test_get_treatment_record_not_found(self, mock_db):
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = result_mock

        with pytest.raises(NotFoundError, match="Treatment record not found"):
            await TreatmentRecordService.get_treatment_record(
                mock_db, uuid4(), "u"
            )

    @pytest.mark.asyncio
    async def test_get_treatment_record_forbidden(self, mock_db, mock_record):
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = mock_record
        mock_db.execute.return_value = result_mock

        with pytest.raises(ForbiddenError, match="Access denied"):
            await TreatmentRecordService.get_treatment_record(
                mock_db, mock_record.uuid, "wrong-user"
            )

    @pytest.mark.asyncio
    @patch(
        "src.services.treatment_record_service.TreatmentService.get_treatment_by_uuid"
    )
    async def test_get_treatment_records(
        self, mock_get_treatment, mock_db, mock_record, mock_treatment
    ):
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [mock_record]
        mock_db.execute.return_value = result_mock

        records = await TreatmentRecordService.get_treatment_records(
            mock_db,
            mock_treatment.uuid,
            "user-123",
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
        )

        assert records == [mock_record]
        mock_get_treatment.assert_called_once()

    @pytest.mark.asyncio
    @patch(
        "src.services.treatment_record_service.TreatmentService.get_treatment_by_uuid"
    )
    async def test_create_treatment_record(
        self, mock_get_treatment, mock_db, mock_treatment
    ):
        schema = TreatmentRecordCreate(
            treatment_uuid=mock_treatment.uuid,
            content="New content",
            date=date(2023, 2, 1),
            start_time=time(9, 0),
            end_time=time(10, 0),
        )

        # Mock max record number query
        max_res = MagicMock()
        max_res.scalar.return_value = 5
        mock_db.execute.return_value = max_res

        record = await TreatmentRecordService.create_treatment_record(
            mock_db, schema, "user-123"
        )

        assert record.record_number == 6
        assert record.content == "New content"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_treatment_record(self, mock_db, mock_record):
        # Mock get_treatment_record internally
        res_get = MagicMock()
        res_get.scalars.return_value.first.return_value = mock_record
        mock_db.execute.return_value = res_get

        schema = TreatmentRecordUpdate(content="Updated content")

        updated = await TreatmentRecordService.update_treatment_record(
            mock_db, mock_record.uuid, "user-123", schema
        )

        assert updated.content == "Updated content"
        mock_db.commit.assert_called_once()
