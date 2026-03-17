from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.core.exceptions import ForbiddenError, NotFoundError
from src.models import Treatment, TreatmentReport
from src.schemas.treatment_report_schema import (
    TreatmentReportCreate,
    TreatmentReportUpdate,
)
from src.services.treatment_report_service import TreatmentReportService


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
def mock_report(mock_treatment):
    report = MagicMock(spec=TreatmentReport)
    report.uuid = uuid4()
    report.treatment_uuid = mock_treatment.uuid
    report.issue_date = date(2023, 1, 1)
    report.treatment = mock_treatment
    return report


class TestTreatmentReportServiceCRUD:
    @pytest.mark.asyncio
    async def test_get_treatment_report_success(self, mock_db, mock_report):
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = mock_report
        mock_db.execute.return_value = result_mock

        report = await TreatmentReportService.get_treatment_report(
            mock_db, mock_report.uuid, "user-123"
        )

        assert report == mock_report

    @pytest.mark.asyncio
    async def test_get_treatment_report_not_found(self, mock_db):
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = result_mock

        with pytest.raises(NotFoundError, match="Treatment report not found"):
            await TreatmentReportService.get_treatment_report(
                mock_db, uuid4(), "u"
            )

    @pytest.mark.asyncio
    async def test_get_treatment_report_forbidden(self, mock_db, mock_report):
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = mock_report
        mock_db.execute.return_value = result_mock

        with pytest.raises(ForbiddenError, match="Access denied"):
            await TreatmentReportService.get_treatment_report(
                mock_db, mock_report.uuid, "wrong-user"
            )

    @pytest.mark.asyncio
    @patch(
        "src.services.treatment_report_service.TreatmentService.get_treatment_by_uuid"
    )
    async def test_get_treatment_reports(
        self, mock_get_treatment, mock_db, mock_report, mock_treatment
    ):
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [mock_report]
        mock_db.execute.return_value = result_mock

        reports = await TreatmentReportService.get_treatment_reports(
            mock_db,
            mock_treatment.uuid,
            "user-123",
            start_date=date(2023, 1, 1),
            end_date=date(2023, 3, 1),
        )

        assert reports == [mock_report]
        mock_get_treatment.assert_called_once()

    @pytest.mark.asyncio
    @patch(
        "src.services.treatment_report_service.TreatmentService.get_treatment_by_uuid"
    )
    async def test_create_treatment_report(
        self, mock_get_treatment, mock_db, mock_treatment
    ):
        schema = TreatmentReportCreate(
            treatment_uuid=mock_treatment.uuid,
            issue_date=date(2023, 2, 1),
            start_date_period=date(2023, 1, 1),
            end_date_period=date(2023, 1, 31),
            demand_description="demand",
            procedures="procs",
            analysis="anal",
            conclusion="conc",
        )

        report = await TreatmentReportService.create_treatment_report(
            mock_db, schema, "user-123"
        )

        assert report.issue_date == date(2023, 2, 1)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_treatment_report(self, mock_db, mock_report):
        # Mock get_treatment_report internally
        res_get = MagicMock()
        res_get.scalars.return_value.first.return_value = mock_report
        mock_db.execute.return_value = res_get

        schema = TreatmentReportUpdate(demand_description="Updated demand")

        updated = await TreatmentReportService.update_treatment_report(
            mock_db, mock_report.uuid, "user-123", schema
        )

        assert updated.demand_description == "Updated demand"
        mock_db.commit.assert_called_once()
