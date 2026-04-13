from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.usage_statistic import ProcessType
from src.services.dashboard_service import DashboardService


class TestDashboardService:
    @pytest.mark.asyncio
    async def test_get_usage_aggregates(self, mock_db):
        user_uuid = "test-user-uuid"
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)

        # Mock stats_result
        stats_row = MagicMock()
        stats_row.total_input_tokens = 100
        stats_row.total_output_tokens = 200
        stats_row.total_audio_duration = 300.0
        stats_row.total_audio_duration_after_vad = 250.0

        stats_result_mock = MagicMock()
        stats_result_mock.one.return_value = stats_row

        # Mock process_counts_result
        process_row1 = MagicMock()
        process_row1.process_type = ProcessType.TRANSCRIPTION
        process_row1.count = 5

        process_row2 = MagicMock()
        process_row2.process_type = ProcessType.RECORD_GENERATION
        process_row2.count = 3

        process_counts_result_mock = MagicMock()
        process_counts_result_mock.all.return_value = [process_row1, process_row2]

        # Side effect for multiple execute calls
        mock_db.execute.side_effect = [stats_result_mock, process_counts_result_mock]

        res_stats_row, process_counts = await DashboardService._get_usage_aggregates(
            mock_db, user_uuid, start_date, end_date
        )

        assert res_stats_row.total_input_tokens == 100
        assert process_counts[ProcessType.TRANSCRIPTION] == 5
        assert process_counts[ProcessType.RECORD_GENERATION] == 3
        assert mock_db.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_get_entity_counts(self, mock_db):
        user_uuid = "test-user-uuid"
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)

        active_result = MagicMock()
        active_result.scalar.return_value = 10

        records_result = MagicMock()
        records_result.scalar.return_value = 20

        reports_result = MagicMock()
        reports_result.scalar.return_value = 30

        mock_db.execute.side_effect = [active_result, records_result, reports_result]

        active_count, records_count, reports_count = await DashboardService._get_entity_counts(
            mock_db, user_uuid, start_date, end_date
        )

        assert active_count == 10
        assert records_count == 20
        assert reports_count == 30
        assert mock_db.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_get_dashboard_with_dates(self, mock_db):
        user_uuid = "test-user-uuid"
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)

        stats_row = MagicMock()
        stats_row.total_input_tokens = 100
        stats_row.total_output_tokens = 200
        stats_row.total_audio_duration = 300.0
        stats_row.total_audio_duration_after_vad = 250.0

        process_counts = {
            ProcessType.TRANSCRIPTION: 5,
            ProcessType.RECORD_GENERATION: 3,
            ProcessType.REPORT_GENERATION: 2,
        }

        with patch.object(
            DashboardService, "_get_usage_aggregates", return_value=(stats_row, process_counts)
        ) as mock_usage, patch.object(
            DashboardService, "_get_entity_counts", return_value=(10, 20, 30)
        ) as mock_entities:
            response = await DashboardService.get_dashboard(
                mock_db, user_uuid, start_date, end_date
            )

            assert response.total_input_tokens == 100
            assert response.total_transcriptions == 5
            assert response.active_treatments_count == 10
            assert response.start_date == start_date
            assert response.end_date == end_date
            mock_usage.assert_called_once_with(mock_db, user_uuid, start_date, end_date)
            mock_entities.assert_called_once_with(mock_db, user_uuid, start_date, end_date)

    @pytest.mark.asyncio
    async def test_get_dashboard_default_dates(self, mock_db):
        user_uuid = "test-user-uuid"
        today = date.today()
        thirty_days_ago = today - timedelta(days=30)

        stats_row = MagicMock()
        stats_row.total_input_tokens = 0
        stats_row.total_output_tokens = 0
        stats_row.total_audio_duration = 0.0
        stats_row.total_audio_duration_after_vad = 0.0

        process_counts = {}

        with patch.object(
            DashboardService, "_get_usage_aggregates", return_value=(stats_row, process_counts)
        ), patch.object(
            DashboardService, "_get_entity_counts", return_value=(0, 0, 0)
        ):
            response = await DashboardService.get_dashboard(mock_db, user_uuid)

            assert response.start_date == thirty_days_ago
            assert response.end_date == today
