import asyncio
import logging
from uuid import UUID

from src.ai.exceptions import AIFatalError, AITransientError
from src.celery_app import celery_app
from src.database import get_async_session
from src.services.treatment_context_service import (
    TreatmentContextService,
)

logger = logging.getLogger(__name__)


async def generate_context_draft_logic(
    treatment_uuid: str,
    treatment_record_uuid: str,
    user_uuid: str,
):
    logger.info(
        "Iniciando generate_context_draft_logic para "
        "tratamento %s (prontuário %s)",
        treatment_uuid,
        treatment_record_uuid,
    )
    db = await get_async_session()
    try:
        await TreatmentContextService.generate_context_draft(
            db=db,
            treatment_uuid=UUID(treatment_uuid),
            treatment_record_uuid=UUID(treatment_record_uuid),
            user_uuid=user_uuid,
        )
        logger.info(
            "generate_context_draft_logic concluído "
            "com sucesso para tratamento %s",
            treatment_uuid,
        )
    finally:
        await db.close()


def do_generate_context_draft(
    treatment_uuid: str,
    treatment_record_uuid: str,
    user_uuid: str,
):
    try:
        asyncio.run(
            generate_context_draft_logic(
                treatment_uuid,
                treatment_record_uuid,
                user_uuid,
            )
        )
    except AITransientError as e:
        logger.warning(
            "Erro transitório ao gerar context draft: %s",
            str(e),
        )
        raise

    except AIFatalError as e:
        logger.error(
            "Erro fatal ao gerar context draft: %s",
            str(e),
        )
        # Fatal errors should not be retried
        return

    except Exception:
        logger.exception("Erro inesperado na task de context draft")
        # Don't retry unknown errors
        return


@celery_app.task(
    name="Gerar draft de contexto clínico",
    retry_backoff=30,
    autoretry_for=(AITransientError,),
    retry_kwargs={"max_retries": 5},
    acks_late=True,
)
def generate_context_draft_task(
    treatment_uuid: str,
    treatment_record_uuid: str,
    user_uuid: str,
):
    return do_generate_context_draft(
        treatment_uuid,
        treatment_record_uuid,
        user_uuid,
    )
