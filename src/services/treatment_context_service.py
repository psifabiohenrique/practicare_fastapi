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


def _merge_diffs(old_diff: dict | None, new_diff: dict | None) -> dict | None:
    """
    Merges two ContextFieldDiff dicts by combining their add/remove lists,
    deduplicating items.
    Returns None if both are None.
    """
    if old_diff is None and new_diff is None:
        return None

    old_add = (old_diff or {}).get("add", [])
    old_remove = (old_diff or {}).get("remove", [])
    new_add = (new_diff or {}).get("add", [])
    new_remove = (new_diff or {}).get("remove", [])

    # Merge and deduplicate preserving order
    merged_add = list(dict.fromkeys(old_add + new_add))
    merged_remove = list(dict.fromkeys(old_remove + new_remove))

    if not merged_add and not merged_remove:
        return None

    return {"add": merged_add, "remove": merged_remove}


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
        context = await TreatmentContextService.get_or_create_context(
            db, treatment_uuid, user_uuid
        )

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
        Directly patches the TreatmentContext with list[str] per field.
        Creates it if it doesn't exist yet.
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
        draft_data is a dict where each key in CONTEXT_FIELDS maps to
        either None or {"add": [...], "remove": [...]}.
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
        Applies a draft: updates the TreatmentContext with the
        user-reviewed final list[str] per field and marks draft as applied.
        The frontend is responsible for computing the final lists after
        accepting/rejecting individual bullet suggestions.
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

        # Apply user-reviewed data to context
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
        If there is a pending draft for this context, merges its
        add/remove lists with the new draft data (deduplicating) and
        marks the old draft as applied (without applying to context).
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
            "Mesclando draft pendente %s ao novo draft",
            pending_draft.uuid,
        )

        merged = {}
        for field in CONTEXT_FIELDS:
            old_diff = getattr(pending_draft, field)
            new_diff = new_draft_data.get(field)
            merged[field] = _merge_diffs(old_diff, new_diff)

        # Mark old draft as applied (without applying to context)
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
        Orchestrates the AI call to generate a context update draft
        (structured add/remove diffs) from a new treatment record.
        """
        logger.info(
            "Gerando context draft para tratamento %s (prontuário %s)",
            treatment_uuid,
            treatment_record_uuid,
        )

        context = await TreatmentContextService.get_or_create_context(
            db, treatment_uuid, user_uuid
        )

        # Build current context dict (list[str] per field)
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
        merged_data = await TreatmentContextService._merge_pending_draft_into(
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

    @staticmethod
    async def schedule_context_generation(
        db: AsyncSession,
        treatment_uuid: UUID,
        user_uuid: str,
        historical_notes: str | None,
        include_existing_records: bool,
    ) -> TreatmentContext:
        """
        Sets is_update_scheduled = True and schedules the celery task.
        """
        context = await TreatmentContextService.get_or_create_context(
            db, treatment_uuid, user_uuid
        )

        if context.is_update_scheduled:
            raise ForbiddenError(
                "An update is already scheduled for this context"
            )

        context.is_update_scheduled = True
        db.add(context)
        await db.commit()
        await db.refresh(context)

        # Import task here to avoid circular imports
        from src.tasks.context_generation import (  # noqa: E402
            generate_context_from_history_task,
        )

        generate_context_from_history_task.delay(
            str(treatment_uuid),
            user_uuid,
            historical_notes,
            include_existing_records,
        )

        return context

    @staticmethod
    async def generate_context_from_history(  # noqa: PLR0913, PLR0912
        db: AsyncSession,
        treatment_uuid: UUID,
        user_uuid: str,
        historical_notes: str | None,
        include_existing_records: bool,
    ):
        """
        Orchestrates the AI call to generate the full context as a draft
        with list[str] per field. Resets is_update_scheduled = False at end.
        """
        from src.ai.chains.context_generation import (  # noqa: E402
            ContextGenerationChain,
        )
        from src.models.treatment_record_model import (  # noqa: E402
            TreatmentRecord,
        )

        context = await TreatmentContextService.get_or_create_context(
            db, treatment_uuid, user_uuid
        )

        try:
            # Get patient gender
            treatment_patient = await (
                PatientWithTreatmentService.get_patient_with_treatment_uuid(
                    db=db,
                    treatment_uuid=treatment_uuid,
                    user_uuid=user_uuid,
                )
            )

            # Assemble base material
            base_material = ""
            if historical_notes:
                base_material += (
                    "=== HISTÓRICO DE ANOTAÇÕES PRÉVIAS ===\n"
                    f"{historical_notes}\n\n"
                )

            if include_existing_records:
                records_result = await db.execute(
                    select(TreatmentRecord)
                    .filter(
                        TreatmentRecord.treatment_uuid == str(treatment_uuid)
                    )
                    .order_by(TreatmentRecord.date.asc())
                )
                records = records_result.scalars().all()
                if records:
                    base_material += "=== PRONTUÁRIOS DO SISTEMA ===\n"
                    for r in records:
                        base_material += (
                            f"Data: {r.date.isoformat()}\n"
                            f"Tipo: {r.type}\n"
                            f"Conteúdo: {r.content}\n\n"
                        )

            if not base_material.strip():
                # Nothing to process. Just clear lock
                return

            chain = ContextGenerationChain()
            result = await chain.generate(
                base_material=base_material,
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

            # The generation result is list[str] per field — we wrap it as
            # a draft with add=[...] and remove=[] so the user can review
            # before applying.
            wrapped_draft_data = {}
            for field in CONTEXT_FIELDS:
                bullets = draft_data.get(field)
                if bullets:
                    wrapped_draft_data[field] = {
                        "add": bullets,
                        "remove": [],
                    }
                else:
                    wrapped_draft_data[field] = None

            # Clear ALL pending drafts before creating the new one
            draft_result = await db.execute(
                select(TreatmentContextDraft).filter(
                    TreatmentContextDraft.treatment_context_uuid
                    == str(context.uuid),
                    TreatmentContextDraft.is_applied.is_(False),
                )
            )
            pending_drafts = draft_result.scalars().all()
            for pd in pending_drafts:
                pd.is_applied = True
                db.add(pd)
            await db.flush()

            latest_record_result = await db.execute(
                select(TreatmentRecord)
                .filter(TreatmentRecord.treatment_uuid == str(treatment_uuid))
                .order_by(TreatmentRecord.date.desc())
                .limit(1)
            )
            latest_record = latest_record_result.scalars().first()
            if not latest_record:
                # No record exists — apply directly to context
                for field in CONTEXT_FIELDS:
                    bullets = draft_data.get(field)
                    setattr(context, field, bullets or None)
            else:
                await TreatmentContextService.create_draft(
                    db=db,
                    treatment_context_uuid=context.uuid,
                    treatment_record_uuid=latest_record.uuid,
                    draft_data=wrapped_draft_data,
                )

        finally:
            context.is_update_scheduled = False
            db.add(context)
            await db.commit()
