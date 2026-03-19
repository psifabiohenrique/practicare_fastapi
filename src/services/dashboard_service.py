import logging
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.treatment_model import Treatment, TreatmentStatus
from src.models.treatment_record_model import TreatmentRecord
from src.models.treatment_report_model import TreatmentReport
from src.models.usage_statistic import ProcessType, UsageStatistic
from src.schemas.dashboard_schema import DashboardResponse

logger = logging.getLogger(__name__)


class DashboardService:
    @staticmethod
    async def _get_usage_aggregates(
        db: AsyncSession,
        user_uuid: str,
        start_date: date,
        end_date: date,
    ) -> tuple:
        """Aggregate token usage and duration statistics."""
        stats_query = select(
            func.coalesce(func.sum(UsageStatistic.input_tokens), 0).label(
                "total_input_tokens"
            ),
            func.coalesce(func.sum(UsageStatistic.output_tokens), 0).label(
                "total_output_tokens"
            ),
            func.coalesce(
                func.sum(UsageStatistic.audio_duration_seconds), 0.0
            ).label("total_audio_duration"),
            func.coalesce(
                func.sum(UsageStatistic.audio_duration_after_vad_seconds), 0.0
            ).label("total_audio_duration_after_vad"),
        ).filter(
            UsageStatistic.user_uuid == user_uuid,
            func.date(UsageStatistic.created_at) >= start_date,
            func.date(UsageStatistic.created_at) <= end_date,
        )
        stats_result = await db.execute(stats_query)
        stats_row = stats_result.one()

        process_counts_query = (
            select(
                UsageStatistic.process_type,
                func.count().label("count"),
            )
            .filter(
                UsageStatistic.user_uuid == user_uuid,
                func.date(UsageStatistic.created_at) >= start_date,
                func.date(UsageStatistic.created_at) <= end_date,
            )
            .group_by(UsageStatistic.process_type)
        )
        process_counts_result = await db.execute(process_counts_query)
        process_counts = {
            row.process_type: row.count for row in process_counts_result.all()
        }

        return stats_row, process_counts

    @staticmethod
    async def _get_entity_counts(
        db: AsyncSession,
        user_uuid: str,
        start_date: date,
        end_date: date,
    ) -> tuple[int, int, int]:
        """Count active treatments, records, and reports."""
        user_treatments = select(Treatment.uuid).filter(
            Treatment.user_uuid == user_uuid
        )

        active_q = select(func.count()).filter(
            Treatment.user_uuid == user_uuid,
            Treatment.status == TreatmentStatus.ACTIVE,
        )
        active_result = await db.execute(active_q)
        active_count = active_result.scalar() or 0

        records_q = select(func.count()).filter(
            TreatmentRecord.created_at >= start_date,
            TreatmentRecord.created_at <= end_date,
            TreatmentRecord.treatment_uuid.in_(user_treatments),
        )
        records_result = await db.execute(records_q)
        records_count = records_result.scalar() or 0

        reports_q = select(func.count()).filter(
            TreatmentReport.created_at >= start_date,
            TreatmentReport.created_at <= end_date,
            TreatmentReport.treatment_uuid.in_(user_treatments),
        )
        reports_result = await db.execute(reports_q)
        reports_count = reports_result.scalar() or 0

        return active_count, records_count, reports_count

    @staticmethod
    async def get_dashboard(
        db: AsyncSession,
        user_uuid: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> DashboardResponse:
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        (
            stats_row,
            process_counts,
        ) = await DashboardService._get_usage_aggregates(
            db, user_uuid, start_date, end_date
        )
        (
            active_count,
            records_count,
            reports_count,
        ) = await DashboardService._get_entity_counts(
            db, user_uuid, start_date, end_date
        )

        return DashboardResponse(
            total_input_tokens=stats_row.total_input_tokens,
            total_output_tokens=stats_row.total_output_tokens,
            total_audio_duration=stats_row.total_audio_duration,
            total_audio_duration_after_vad=stats_row.total_audio_duration_after_vad,  # noqa: E501
            total_transcriptions=process_counts.get(
                ProcessType.TRANSCRIPTION, 0
            ),
            total_records_generated=process_counts.get(
                ProcessType.RECORD_GENERATION, 0
            ),
            total_reports_generated=process_counts.get(
                ProcessType.REPORT_GENERATION, 0
            ),
            active_treatments_count=active_count,
            records_count=records_count,
            reports_count=reports_count,
            start_date=start_date,
            end_date=end_date,
        )
