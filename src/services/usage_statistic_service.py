import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.usage_statistic import UsageStatistic
from src.schemas.dashboard_schema import UsageStatisticCreate

logger = logging.getLogger(__name__)


class UsageStatisticService:
    @staticmethod
    async def create_statistic(
        db: AsyncSession, schema: UsageStatisticCreate
    ) -> UsageStatistic:
        def _to_uuid(val: str | None) -> uuid.UUID | None:
            if not val:
                return None
            if isinstance(val, uuid.UUID):
                return val
            return uuid.UUID(val)

        statistic = UsageStatistic(
            user_uuid=_to_uuid(schema.user_uuid),
            job_uuid=_to_uuid(schema.job_uuid),
            process_type=schema.process_type,
            input_tokens=schema.input_tokens,
            output_tokens=schema.output_tokens,
            audio_duration_seconds=schema.audio_duration_seconds,
            audio_duration_after_vad_seconds=schema.audio_duration_after_vad_seconds,  # noqa: E501
        )
        db.add(statistic)
        await db.commit()
        await db.refresh(statistic)
        logger.info(
            f"Estatística de uso registrada para o job: {schema.job_uuid}",
            extra={
                "job_uuid": str(schema.job_uuid),
                "process_type": schema.process_type,
            },
        )
        return statistic
