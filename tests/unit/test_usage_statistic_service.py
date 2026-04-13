from unittest.mock import AsyncMock

import pytest

import uuid
from src.schemas.dashboard_schema import ProcessType, UsageStatisticCreate
from src.services.usage_statistic_service import UsageStatisticService


class TestUsageStatisticService:
    @pytest.mark.asyncio
    async def test_create_statistic(self, mock_db):
        user_id = uuid.uuid4()
        job_id = uuid.uuid4()
        schema = UsageStatisticCreate(
            user_uuid=user_id,
            job_uuid=job_id,
            process_type=ProcessType.TRANSCRIPTION,
            input_tokens=100,
            output_tokens=200,
            audio_duration_seconds=300.0,
            audio_duration_after_vad_seconds=250.0
        )

        # We need to mock the refresh since it doesn't do anything on AsyncMock by default
        # but the code expects the object to have the values
        async def mock_refresh(instance):
            instance.user_uuid = user_id
            instance.job_uuid = job_id
            instance.input_tokens = 100
        mock_db.refresh.side_effect = mock_refresh

        result = await UsageStatisticService.create_statistic(mock_db, schema)

        assert result.user_uuid == user_id
        assert result.job_uuid == job_id
        assert result.input_tokens == schema.input_tokens
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_statistic_with_none_and_uuid_obj(self, mock_db):
        user_uuid = uuid.uuid4()
        schema = UsageStatisticCreate(
            user_uuid=user_uuid, # Pass as UUID object
            job_uuid=None,       # Pass as None
            process_type=ProcessType.TRANSCRIPTION,
            input_tokens=100,
            output_tokens=200
        )
        
        async def mock_refresh(instance):
            pass
        mock_db.refresh.side_effect = mock_refresh
        
        result = await UsageStatisticService.create_statistic(mock_db, schema)
        assert result.user_uuid == user_uuid
        assert result.job_uuid is None

    @pytest.mark.asyncio
    async def test_create_statistic_with_string_uuid(self, mock_db):
        user_uuid_str = str(uuid.uuid4())
        schema = UsageStatisticCreate(
            user_uuid=user_uuid_str,
            process_type=ProcessType.TRANSCRIPTION,
            input_tokens=50,
            output_tokens=50
        )
        
        async def mock_refresh(instance):
            pass
        mock_db.refresh.side_effect = mock_refresh
        
        result = await UsageStatisticService.create_statistic(mock_db, schema)
        assert str(result.user_uuid) == user_uuid_str
