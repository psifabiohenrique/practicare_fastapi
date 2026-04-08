import logging
from uuid import UUID

from fastapi import APIRouter, status

from src.routers.deps import CurrentUser, SessionDB
from src.schemas.treatment_context_schema import (
    TreatmentContextApplyDraft,
    TreatmentContextGenerate,
    TreatmentContextRead,
    TreatmentContextUpdate,
    TreatmentContextWithDraftRead,
)
from src.services.treatment_context_service import (
    TreatmentContextService,
)

router = APIRouter(
    prefix="/treatment-contexts",
    tags=["Treatment contexts"],
)
logger = logging.getLogger(__name__)


@router.get(
    "/treatment/{treatment_uuid}",
    response_model=TreatmentContextWithDraftRead,
)
async def get_context_with_draft(
    treatment_uuid: UUID,
    db: SessionDB,
    current_user: CurrentUser,
) -> any:
    logger.info(
        "Buscando contexto para tratamento %s",
        treatment_uuid,
        extra={
            "user_uuid": str(current_user.uuid),
            "treatment_uuid": str(treatment_uuid),
        },
    )
    (
        context,
        pending_draft,
    ) = await TreatmentContextService.get_context_with_pending_draft(  # noqa: E501
        db, treatment_uuid, current_user.uuid
    )
    return {
        "context": context,
        "pending_draft": pending_draft,
    }


@router.patch(
    "/treatment/{treatment_uuid}",
    response_model=TreatmentContextRead,
)
async def update_context(
    treatment_uuid: UUID,
    schema: TreatmentContextUpdate,
    db: SessionDB,
    current_user: CurrentUser,
) -> any:
    logger.info(
        "Atualizando contexto diretamente para tratamento %s",
        treatment_uuid,
        extra={
            "user_uuid": str(current_user.uuid),
            "treatment_uuid": str(treatment_uuid),
        },
    )
    return await TreatmentContextService.update_context(
        db, treatment_uuid, current_user.uuid, schema
    )


@router.post(
    "/draft/{draft_uuid}/apply",
    response_model=TreatmentContextRead,
)
async def apply_draft(
    draft_uuid: UUID,
    schema: TreatmentContextApplyDraft,
    db: SessionDB,
    current_user: CurrentUser,
) -> any:
    logger.info(
        "Aplicando draft %s",
        draft_uuid,
        extra={
            "user_uuid": str(current_user.uuid),
            "draft_uuid": str(draft_uuid),
        },
    )
    return await TreatmentContextService.apply_draft(
        db, draft_uuid, current_user.uuid, schema
    )


@router.post(
    "/draft/{draft_uuid}/reject",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def reject_draft(
    draft_uuid: UUID,
    db: SessionDB,
    current_user: CurrentUser,
):
    logger.info(
        "Rejeitando draft %s",
        draft_uuid,
        extra={
            "user_uuid": str(current_user.uuid),
            "draft_uuid": str(draft_uuid),
        },
    )
    await TreatmentContextService.reject_draft(
        db, draft_uuid, current_user.uuid
    )


@router.post(
    "/treatment/{treatment_uuid}/generate",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TreatmentContextRead,
)
async def generate_context(
    treatment_uuid: UUID,
    schema: TreatmentContextGenerate,
    db: SessionDB,
    current_user: CurrentUser,
) -> any:
    logger.info(
        "Agendando geração de contexto para tratamento %s",
        treatment_uuid,
        extra={
            "user_uuid": str(current_user.uuid),
            "treatment_uuid": str(treatment_uuid),
        },
    )
    return await TreatmentContextService.schedule_context_generation(
        db,
        treatment_uuid,
        current_user.uuid,
        schema.historical_notes,
        schema.include_existing_records,
    )
