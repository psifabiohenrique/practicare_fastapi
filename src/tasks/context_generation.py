import asyncio
import logging
from uuid import UUID

from src.ai.exceptions import AIFatalError, AITransientError
from src.celery_app import celery_app
from src.database import get_async_session
from src.services.treatment_context_service import TreatmentContextService

logger = logging.getLogger(__name__)


async def generate_context_from_history_logic(
    treatment_uuid: str,
    user_uuid: str,
    historical_notes: str | None,
    include_existing_records: bool,
):
    logger.info(
        "Iniciando generate_context_from_history_logic para tratamento %s",
        treatment_uuid,
    )
    db = await get_async_session()
    try:
        await TreatmentContextService.generate_context_from_history(
            db=db,
            treatment_uuid=UUID(treatment_uuid),
            user_uuid=user_uuid,
            historical_notes=historical_notes,
            include_existing_records=include_existing_records,
        )
        logger.info(
            "generate_context_from_history_logic concluído "
            "com sucesso para tratamento %s",
            treatment_uuid,
        )
    finally:
        await db.close()


def do_generate_context_from_history(
    treatment_uuid: str,
    user_uuid: str,
    historical_notes: str | None,
    include_existing_records: bool,
):
    try:
        asyncio.run(
            generate_context_from_history_logic(
                treatment_uuid,
                user_uuid,
                historical_notes,
                include_existing_records,
            )
        )
    except AITransientError as e:
        logger.warning(
            "Erro transitório ao gerar contexto completo: %s",
            str(e),
        )
        raise

    except AIFatalError as e:
        logger.error(
            "Erro fatal ao gerar contexto completo: %s",
            str(e),
        )
        # Fatal errors should not be retried
        return

    except Exception:
        logger.exception("Erro inesperado na task de context generation")
        raise
    finally:
        # We should reset is_update_scheduled to False after task runs
        # (success or fail). To do this safely async inside sync block,
        # we handle inside the service or a separate async call.
        # Actually it's better handled inside the service's try/finally block.
        pass


@celery_app.task(
    name="Gerar contexto clínico completo",
    retry_backoff=30,
    autoretry_for=(AITransientError,),
    retry_kwargs={"max_retries": 5},
    acks_late=True,
)
def generate_context_from_history_task(
    treatment_uuid: str,
    user_uuid: str,
    historical_notes: str | None,
    include_existing_records: bool,
):
    return do_generate_context_from_history(
        treatment_uuid,
        user_uuid,
        historical_notes,
        include_existing_records,
    )
