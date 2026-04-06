from unittest.mock import AsyncMock

import pytest

import uuid
from src.schemas.dashboard_schema import ProcessType, UsageStatisticCreate
from src.services.usage_statistic_service import UsageStatisticService


@pytest.fixture
def mock_db():
    return AsyncMock()


class TestUsageStatisticService:
    @pytest.mark.asyncio
    async def test_create_statistic(self, mock_db):
        schema = UsageStatisticCreate(
            user_uuid=str(uuid.uuid4()),
            job_uuid=str(uuid.uuid4()),
            process_type=ProcessType.TRANSCRIPTION,
            input_tokens=100,
            output_tokens=200,
            audio_duration_seconds=300.0,
            audio_duration_after_vad_seconds=250.0
        )

        # We need to mock the refresh since it doesn't do anything on AsyncMock by default
        # but the code expects the object to have the values
        async def mock_refresh(instance):
            pass
        mock_db.refresh.side_effect = mock_refresh

        result = await UsageStatisticService.create_statistic(mock_db, schema)

        assert str(result.user_uuid) == schema.user_uuid
        assert result.input_tokens == schema.input_tokens
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
