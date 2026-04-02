import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.chains.context_update import ContextUpdateChain
from src.core.exceptions import ForbiddenError, NotFoundError
from src.models.treatment_context_model import (
    TreatmentContext,
    TreatmentContextDraft,
)
from src.models.usage_statistic import ProcessType
from src.schemas.dashboard_schema import UsageStatisticCreate
from src.schemas.treatment_context_schema import (
    TreatmentContextApplyDraft,
    TreatmentContextUpdate,
)
from src.services.patient_with_treatment_service import (
    PatientWithTreatmentService,
)
from src.services.treatment_record_service import (
    TreatmentRecordService,
)
from src.services.treatment_service import TreatmentService
from src.services.usage_statistic_service import (
    UsageStatisticService,
)

logger = logging.getLogger(__name__)

CONTEXT_FIELDS = [
    "life_dynamics",
    "clinical_history",
    "psychological_patterns",
    "therapeutic_goals",
    "medication_notes",
]


class TreatmentContextService:
    @staticmethod
    async def get_context_with_pending_draft(
        db: AsyncSession,
        treatment_uuid: UUID,
        user_uuid: str,
    ):
        """
        Returns the TreatmentContext and the most recent
        pending (is_applied=False) draft for a treatment.
        """
        await TreatmentService.get_treatment_by_uuid(
            db, treatment_uuid, user_uuid
        )

        result = await db.execute(
            select(TreatmentContext).filter(
                TreatmentContext.treatment_uuid == str(treatment_uuid)
            )
        )
        context = result.scalars().first()

        pending_draft = None
        if context:
            draft_result = await db.execute(
                select(TreatmentContextDraft)
                .filter(
                    TreatmentContextDraft.treatment_context_uuid
                    == str(context.uuid),
                    TreatmentContextDraft.is_applied.is_(False),
                )
                .order_by(TreatmentContextDraft.created_at.desc())
                .limit(1)
            )
            pending_draft = draft_result.scalars().first()

        return context, pending_draft

    @staticmethod
    async def get_or_create_context(
        db: AsyncSession,
        treatment_uuid: UUID,
        user_uuid: str,
    ) -> TreatmentContext:
        """
        Gets the existing TreatmentContext for a treatment,
        or creates an empty one if it doesn't exist.
        """
        await TreatmentService.get_treatment_by_uuid(
            db, treatment_uuid, user_uuid
        )

        result = await db.execute(
            select(TreatmentContext).filter(
                TreatmentContext.treatment_uuid == str(treatment_uuid)
            )
        )
        context = result.scalars().first()

        if not context:
            logger.info(
                "Criando TreatmentContext para o tratamento: %s",
                treatment_uuid,
            )
            context = TreatmentContext(
                treatment_uuid=str(treatment_uuid),
            )
            db.add(context)
            await db.commit()
            await db.refresh(context)
            logger.info(
                "TreatmentContext %s criado com sucesso",
                context.uuid,
            )

        return context

    @staticmethod
    async def update_context(
        db: AsyncSession,
        treatment_uuid: UUID,
        user_uuid: str,
        schema: TreatmentContextUpdate,
    ) -> TreatmentContext:
        """
        Directly patches the TreatmentContext. Creates it
        if it doesn't exist yet.
        """
        context = await TreatmentContextService.get_or_create_context(
            db, treatment_uuid, user_uuid
        )

        logger.info(
            "Atualizando TreatmentContext %s diretamente",
            context.uuid,
        )
        update_data = schema.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(context, key, value)

        db.add(context)
        await db.commit()
        await db.refresh(context)
        return context

    @staticmethod
    async def create_draft(
        db: AsyncSession,
        treatment_context_uuid: UUID,
        treatment_record_uuid: UUID,
        draft_data: dict,
    ) -> TreatmentContextDraft:
        """
        Creates a new TreatmentContextDraft.
        """
        logger.info(
            "Criando TreatmentContextDraft para o contexto %s (prontuário %s)",
            treatment_context_uuid,
            treatment_record_uuid,
        )
        draft = TreatmentContextDraft(
            treatment_context_uuid=str(treatment_context_uuid),
            treatment_record_uuid=str(treatment_record_uuid),
            **{k: v for k, v in draft_data.items() if k in CONTEXT_FIELDS},
        )
        db.add(draft)
        await db.commit()
        await db.refresh(draft)
        logger.info(
            "TreatmentContextDraft %s criado com sucesso",
            draft.uuid,
        )
        return draft

    @staticmethod
    async def _get_draft_with_auth(
        db: AsyncSession,
        draft_uuid: UUID,
        user_uuid: str,
    ) -> TreatmentContextDraft:
        """
        Gets a draft and validates ownership through the
        context -> treatment chain.
        """
        result = await db.execute(
            select(TreatmentContextDraft).filter(
                TreatmentContextDraft.uuid == str(draft_uuid)
            )
        )
        draft = result.scalars().first()
        if not draft:
            raise NotFoundError("Treatment context draft not found")

        # Validate ownership through context -> treatment
        ctx_result = await db.execute(
            select(TreatmentContext).filter(
                TreatmentContext.uuid == str(draft.treatment_context_uuid)
            )
        )
        context = ctx_result.scalars().first()
        if not context:
            raise NotFoundError("Treatment context not found")

        await TreatmentService.get_treatment_by_uuid(
            db, context.treatment_uuid, user_uuid
        )
        return draft

    @staticmethod
    async def apply_draft(
        db: AsyncSession,
        draft_uuid: UUID,
        user_uuid: str,
        final_data: TreatmentContextApplyDraft,
    ) -> TreatmentContext:
        """
        Applies a draft: updates the TreatmentContext with
        the user-edited final data and marks the draft as
        applied.
        """
        draft = await TreatmentContextService._get_draft_with_auth(
            db, draft_uuid, user_uuid
        )

        if draft.is_applied:
            raise ForbiddenError("This draft has already been applied")

        # Get the context
        ctx_result = await db.execute(
            select(TreatmentContext).filter(
                TreatmentContext.uuid == str(draft.treatment_context_uuid)
            )
        )
        context = ctx_result.scalars().first()

        logger.info(
            "Aplicando draft %s ao contexto %s",
            draft_uuid,
            context.uuid,
        )

        # Apply user-edited data to context
        update_data = final_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key in CONTEXT_FIELDS:
                setattr(context, key, value)

        draft.is_applied = True

        db.add(context)
        db.add(draft)
        await db.commit()
        await db.refresh(context)
        return context

    @staticmethod
    async def reject_draft(
        db: AsyncSession,
        draft_uuid: UUID,
        user_uuid: str,
    ) -> None:
        """
        Rejects a draft by marking it as applied without
        updating the context.
        """
        draft = await TreatmentContextService._get_draft_with_auth(
            db, draft_uuid, user_uuid
        )

        if draft.is_applied:
            raise ForbiddenError("This draft has already been processed")

        logger.info("Rejeitando draft %s", draft_uuid)
        draft.is_applied = True
        db.add(draft)
        await db.commit()

    @staticmethod
    async def _merge_pending_draft_into(
        db: AsyncSession,
        context: TreatmentContext,
        new_draft_data: dict,
    ) -> dict:
        """
        If there is a pending draft for this context,
        concatenates its content into the new draft data
        and marks the old draft as applied (without
        applying to context).
        """
        draft_result = await db.execute(
            select(TreatmentContextDraft)
            .filter(
                TreatmentContextDraft.treatment_context_uuid
                == str(context.uuid),
                TreatmentContextDraft.is_applied.is_(False),
            )
            .order_by(TreatmentContextDraft.created_at.desc())
            .limit(1)
        )
        pending_draft = draft_result.scalars().first()

        if not pending_draft:
            return new_draft_data

        logger.info(
            "Concatenando draft pendente %s ao novo draft",
            pending_draft.uuid,
        )

        merged = {}
        for field in CONTEXT_FIELDS:
            old_val = getattr(pending_draft, field) or ""
            new_val = new_draft_data.get(field) or ""
            if old_val and new_val and old_val != new_val:
                merged[field] = new_val
            elif new_val:
                merged[field] = new_val
            elif old_val:
                merged[field] = old_val
            else:
                merged[field] = None

        # Mark old draft as applied (without applying)
        pending_draft.is_applied = True
        db.add(pending_draft)
        await db.flush()

        return merged

    @staticmethod
    async def generate_context_draft(  # noqa: PLR0913
        db: AsyncSession,
        treatment_uuid: UUID,
        treatment_record_uuid: UUID,
        user_uuid: str,
    ) -> TreatmentContextDraft:
        """
        Orchestrates the AI call to generate a context
        update draft from a new treatment record.
        """
        logger.info(
            "Gerando context draft para tratamento %s (prontuário %s)",
            treatment_uuid,
            treatment_record_uuid,
        )

        context = await TreatmentContextService.get_or_create_context(
            db, treatment_uuid, user_uuid
        )

        # Build current context dict
        current_ctx = {}
        for field in CONTEXT_FIELDS:
            current_ctx[field] = getattr(context, field)

        # Get the record content
        record = await TreatmentRecordService.get_treatment_record(
            db, treatment_record_uuid, user_uuid
        )

        # Get patient gender
        treatment_patient = (
            await PatientWithTreatmentService.get_patient_with_treatment_uuid(  # noqa: E501
                db=db,
                treatment_uuid=treatment_uuid,
                user_uuid=user_uuid,
            )
        )

        # Call AI
        chain = ContextUpdateChain()
        result = await chain.generate(
            current_context=current_ctx,
            record_content=record.content,
            gender=treatment_patient.gender,
        )

        # Save usage statistic
        await UsageStatisticService.create_statistic(
            db,
            UsageStatisticCreate(
                user_uuid=str(user_uuid),
                process_type=ProcessType.CONTEXT_UPDATE,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
            ),
        )

        draft_data = result.content
        if not isinstance(draft_data, dict):
            draft_data = {}

        # Merge with any pending draft
        merged_data = await TreatmentContextService._merge_pending_draft_into(  # noqa: E501
            db, context, draft_data
        )

        # Create the new draft
        draft = await TreatmentContextService.create_draft(
            db=db,
            treatment_context_uuid=context.uuid,
            treatment_record_uuid=treatment_record_uuid,
            draft_data=merged_data,
        )

        return draft
