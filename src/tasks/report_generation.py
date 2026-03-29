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


async def generate_report_logic(job_uuid: UUID):
    logger.info(
        f"Iniciando generate_report_logic para o job: {job_uuid}",
        extra={"job_uuid": str(job_uuid)},
    )
    db = await get_async_session()
    await AutomatedReportService.update_job_status(
        db=db,
        job_uuid=job_uuid,
        status=ReportJobStatus.GENERATING_REPORT,
    )

    job = await AutomatedReportService.get_job(db, job_uuid)

    await AutomatedReportService.generate_report_content(db, job)
    await db.close()
    logger.info(
        f"generate_report_logic concluído com sucesso para o job: {job_uuid}",
        extra={"job_uuid": str(job_uuid)},
    )


def do_generate_report(job_uuid: UUID):
    try:
        asyncio.run(generate_report_logic(job_uuid))

    except AITransientError as e:
        asyncio.run(
            comunicate_report_fail(
                job_uuid,
                "Falha na comunicação com a IA, uma nova"
                + " tentativa será realizada em breve",
            )
        )
        logger.warning(f"Erro transitório ao gerar relatório. {str(e)}")
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


@celery_app.task(
    name="Gerar relatório",
    # bind=True,
    retry_backoff=30,
    retry_backoff_max=60 * 60,
    autoretry_for=(AITransientError,),
    retry_kwargs={"max_retries": 10},
    acks_late=True,
)
def generate_report_task(job_uuid: UUID):
    return do_generate_report(job_uuid)
