from datetime import time
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.core.exceptions import ForbiddenError, NotFoundError
from src.models import Treatment
from src.schemas.treatment_schema import TreatmentCreate, TreatmentUpdate
from src.services.treatment_service import TreatmentService


@pytest.fixture
def mock_db():
    return AsyncMock()


class TestCreateTreatmentModel:
    def test_creates_treatment_from_schema(self):
        schema = TreatmentCreate(
            weekday="Monday",
            start_time=time(9, 0),
            end_time=time(10, 0),
        )
        treatment = TreatmentService._create_treatment_model(schema)
        assert isinstance(treatment, Treatment)
        assert treatment.weekday == "Monday"
        assert treatment.start_time == time(9, 0)
        assert treatment.end_time == time(10, 0)


class TestApplyUpdate:
    def test_apply_update_partial(self):
        treatment = Treatment(weekday="Monday", start_time=time(9, 0))
        update = TreatmentUpdate(weekday="Friday")
        TreatmentService._apply_update(treatment, update)
        assert treatment.weekday == "Friday"
        assert treatment.start_time == time(9, 0)  # Unchanged

    def test_apply_update_empty(self):
        treatment = Treatment(weekday="Monday")
        update = TreatmentUpdate()
        TreatmentService._apply_update(treatment, update)
        assert treatment.weekday == "Monday"


class TestGetTreatmentByUUID:
    @pytest.mark.asyncio
    async def test_get_treatment_not_found(self, mock_db):
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = result_mock

        with pytest.raises(NotFoundError, match="Treatment not found"):
            await TreatmentService.get_treatment_by_uuid(
                mock_db, uuid4(), str(uuid4())
            )

    @pytest.mark.asyncio
    async def test_get_treatment_forbidden(self, mock_db):
        user_uuid = str(uuid4())
        other_user_uuid = str(uuid4())
        mock_treatment = MagicMock(spec=Treatment)
        mock_treatment.user_uuid = other_user_uuid

        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = mock_treatment
        mock_db.execute.return_value = result_mock

        with pytest.raises(ForbiddenError, match="Access denied"):
            await TreatmentService.get_treatment_by_uuid(
                mock_db, uuid4(), user_uuid
            )

    @pytest.mark.asyncio
    async def test_get_treatment_success(self, mock_db):
        user_uuid = str(uuid4())
        mock_treatment = MagicMock(spec=Treatment)
        mock_treatment.user_uuid = user_uuid

        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = mock_treatment
        mock_db.execute.return_value = result_mock

        result = await TreatmentService.get_treatment_by_uuid(
            mock_db, uuid4(), user_uuid
        )
        assert result == mock_treatment
