import asyncio
import logging
from uuid import UUID

from src.ai.exceptions import AIFatalError, AITransientError
from src.celery_app import celery_app
from src.database import get_async_session
from src.models.automated_report_job import ReportJobStatus
from src.models.treatment_report_model import ReportStatus
from src.schemas.treatment_report_schema import (
    InternalTreatmentReportUpdate,
)
from src.services.automated_report_service import AutomatedReportService
from src.services.treatment_report_service import TreatmentReportService

logger = logging.getLogger(__name__)


async def comunicate_report_fail(job_uuid: UUID, message: str):
    db = await get_async_session()
    job = await AutomatedReportService.get_job(db, job_uuid)
    await TreatmentReportService.update_treatment_report(
        db,
        job.treatment_report_uuid,  # type: ignore
        job.user_uuid,  # type: ignore
        InternalTreatmentReportUpdate(
            demand_description=message,
            procedures=message,
            analysis=message,
            conclusion=message,
            status=ReportStatus.FAILED,
        ),
    )
    await db.close()


async def _generate_report(job_uuid: UUID):
    db = await get_async_session()
    await AutomatedReportService.update_job_status(
        db=db,
        job_uuid=job_uuid,
        status=ReportJobStatus.GENERATING_REPORT,
    )

    job = await AutomatedReportService.get_job(db, job_uuid)

    await AutomatedReportService.generate_report_content(db, job)
    await db.close()


@celery_app.task(
    name="Gerar relatório",
    bind=True,
    retry_backoff=30,
    retry_backoff_max=60 * 60,
    autoretry_for=(AITransientError,),
    retry_kwargs={"max_retries": 10},
    acks_late=True,
)
def generate_report_task(self, job_uuid: UUID):
    try:
        asyncio.run(_generate_report(job_uuid))

    except AITransientError as e:
        asyncio.run(
            comunicate_report_fail(
                job_uuid,
                "Falha na comunicação com a IA, uma nova"
                + " tentativa será realizada em breve",
            )
        )
        logger.warning(
            f"Erro transitório ao gerar relatório. {str(e)}"
        )
        raise

    except AIFatalError as e:
        asyncio.run(
            comunicate_report_fail(
                job_uuid,
                "Uma falha fatal ocorreu ao gerar o relatório.",
            )
        )
        logger.error(
            f"Erro fatal ao gerar relatório: {str(e)}",
        )
        raise

    except Exception:
        # fallback defensivo
        asyncio.run(
            comunicate_report_fail(
                job_uuid,
                "Uma falha inesperada ocorreu ao gerar o relatório.",
            )
        )
        logger.exception("Erro inesperado na task de relatório")
        raise
