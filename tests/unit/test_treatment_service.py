from datetime import time
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.core.exceptions import ForbiddenError, NotFoundError
from src.models import Treatment
from src.schemas import (
    TreatmentCreate,
    TreatmentUpdate,
    TreatmentUpdateInternal,
)
from src.services.treatment_service import TreatmentService


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_treatment():
    treatment = MagicMock(spec=Treatment)
    treatment.uuid = uuid4()
    treatment.user_uuid = "user-123"
    treatment.patient_uuid = uuid4()
    return treatment


class TestTreatmentServiceCRUD:
    @pytest.mark.asyncio
    async def test_get_treatment_by_uuid_success(
        self, mock_db, mock_treatment
    ):
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = mock_treatment
        mock_db.execute.return_value = result_mock

        treatment = await TreatmentService.get_treatment_by_uuid(
            mock_db, mock_treatment.uuid, mock_treatment.user_uuid
        )

        assert treatment == mock_treatment

    @pytest.mark.asyncio
    async def test_get_treatment_by_uuid_not_found(self, mock_db):
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = result_mock

        with pytest.raises(NotFoundError, match="Treatment not found"):
            await TreatmentService.get_treatment_by_uuid(mock_db, uuid4(), "u")

    @pytest.mark.asyncio
    async def test_get_treatment_by_uuid_forbidden(
        self, mock_db, mock_treatment
    ):
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = mock_treatment
        mock_db.execute.return_value = result_mock

        with pytest.raises(ForbiddenError, match="Access denied"):
            await TreatmentService.get_treatment_by_uuid(
                mock_db, mock_treatment.uuid, "wrong-user"
            )

    @pytest.mark.asyncio
    async def test_get_treatments(self, mock_db, mock_treatment):
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [mock_treatment]
        mock_db.execute.return_value = result_mock

        treatments = await TreatmentService.get_treatments(mock_db)

        assert treatments == [mock_treatment]

    @pytest.mark.asyncio
    async def test_create_treatment(self, mock_db):
        treatment_in = TreatmentCreate(
            weekday="Monday",
            start_time=time(9, 0),
            end_time=time(10, 0),
        )

        treatment = await TreatmentService.create_treatment(
            mock_db, treatment_in
        )

        assert treatment.weekday == "Monday"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_treatment(self, mock_db, mock_treatment):
        treatment_in = TreatmentUpdate(weekday="Tuesday")

        updated = await TreatmentService.update_treatment(
            mock_db, mock_treatment, treatment_in
        )

        assert updated.weekday == "Tuesday"
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_treatment_internal(self, mock_db, mock_treatment):
        treatment_in = TreatmentUpdateInternal(status="Inactive")

        updated = await TreatmentService.update_treatment(
            mock_db, mock_treatment, treatment_in
        )

        assert updated.status == "Inactive"
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_treatment(self, mock_db, mock_treatment):
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = mock_treatment
        mock_db.execute.return_value = result_mock

        await TreatmentService.delete_treatment(mock_db, mock_treatment.uuid)

        mock_db.delete.assert_called_once_with(mock_treatment)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_treatment_not_found(self, mock_db):
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = result_mock

        treatment_uuid = uuid4()
        result = await TreatmentService.delete_treatment(mock_db, treatment_uuid)

        assert result is None
        mock_db.delete.assert_not_called()
        mock_db.commit.assert_not_called()
