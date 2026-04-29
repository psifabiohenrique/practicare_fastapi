import logging
from datetime import date
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import ForbiddenError, NotFoundError
from src.models import TreatmentRecord
from src.schemas.treatment_record_schema import (
    TreatmentRecordCreate,
    TreatmentRecordUpdate,
)
from src.services.treatment_service import TreatmentService

logger = logging.getLogger(__name__)

SYSTEM_PLACEHOLDERS = [
    "Processando áudio e gerando prontuário...",
    "Reprocessando o áudio, aguarde...",
]


class TreatmentRecordService:
    @staticmethod
    async def get_treatment_record(
        db: AsyncSession, treatment_record_uuid: UUID, user_uuid: str
    ) -> TreatmentRecord:
        result = await db.execute(
            select(TreatmentRecord)
            .options(selectinload(TreatmentRecord.treatment))
            .filter(TreatmentRecord.uuid == str(treatment_record_uuid))
        )

        record = result.scalars().first()
        if not record:
            logger.warning(
                f"Prontuário não encontrado: {treatment_record_uuid}"
            )
            raise NotFoundError("Treatment record not found")

        if str(record.treatment.user_uuid) != str(user_uuid):
            logger.warning(
                f"Acesso negado ao prontuário {treatment_record_uuid} pelo usuário {user_uuid}"  # noqa: E501
            )
            raise ForbiddenError("Access denied to this treatment record")

        return record

    @staticmethod
    async def get_treatment_records(  # noqa: PLR0913, PLR0917
        db: AsyncSession,
        treatment_uuid: UUID,
        user_uuid: str,
        skip: int = 0,
        limit: int = 100,
        start_date: date | None = None,
        end_date: date | None = None,
        include_archived: bool = False,
    ) -> list[TreatmentRecord]:
        # Check if treatment exists and belongs to user
        await TreatmentService.get_treatment_by_uuid(
            db, treatment_uuid, user_uuid
        )
        query = select(TreatmentRecord).filter(
            TreatmentRecord.treatment_uuid == str(treatment_uuid)
        )

        if not include_archived:
            query = query.filter(TreatmentRecord.is_active)

        if start_date:
            query = query.filter(TreatmentRecord.date >= start_date)
        if end_date:
            query = query.filter(TreatmentRecord.date <= end_date)

        # Get total count for pagination
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        if include_archived:
            query = (
                query
                .order_by(TreatmentRecord.date.desc())
                .offset(skip)
                .limit(limit)
            )
        else:
            query = (
                query
                .order_by(TreatmentRecord.record_number.desc())
                .offset(skip)
                .limit(limit)
            )

        result = await db.execute(query)
        items = list(result.scalars().all())
        return items, total

    @staticmethod
    async def create_treatment_record(
        db: AsyncSession,
        schema: TreatmentRecordCreate,
        user_uuid: str,
        trigger_context_update: bool = True,
    ) -> TreatmentRecord:
        # Check if treatment exists and belongs to user
        await TreatmentService.get_treatment_by_uuid(
            db, schema.treatment_uuid, user_uuid
        )

        logger.info(
            f"Criando novo prontuário para o tratamento: {schema.treatment_uuid}"  # noqa: E501
        )

        # Generate record_number: max(record_number) + 1 for this treatment
        max_number_result = await db.execute(
            select(func.max(TreatmentRecord.record_number)).filter(
                TreatmentRecord.treatment_uuid == str(schema.treatment_uuid)
            )
        )
        current_max = max_number_result.scalar() or 0
        next_number = current_max + 1

        db_treatment_record = TreatmentRecord(
            **schema.model_dump(), record_number=next_number
        )
        db.add(db_treatment_record)
        await db.commit()
        await db.refresh(db_treatment_record)
        logger.info(
            f"Prontuário {db_treatment_record.uuid} (Nº {next_number}) criado com sucesso"  # noqa: E501
        )

        if trigger_context_update and db_treatment_record.content:
            await TreatmentRecordService._trigger_context_update_if_needed(
                db_treatment_record, user_uuid
            )

        return db_treatment_record

    @staticmethod
    async def update_treatment_record(  # noqa: PLR0913
        db: AsyncSession,
        treatment_record_uuid: UUID,
        user_uuid: str,
        schema: TreatmentRecordUpdate,
        trigger_context_update: bool = True,
    ) -> TreatmentRecord:
        db_treatment_record = (
            await TreatmentRecordService.get_treatment_record(
                db, treatment_record_uuid, user_uuid
            )
        )

        logger.info(f"Atualizando prontuário: {treatment_record_uuid}")
        update_data = schema.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(db_treatment_record, key, value)

        db.add(db_treatment_record)
        await db.commit()
        await db.refresh(db_treatment_record)

        if trigger_context_update:
            await TreatmentRecordService._trigger_context_update_if_needed(
                db_treatment_record, user_uuid
            )

        return db_treatment_record

    @staticmethod
    async def delete_treatment_record(
        db: AsyncSession,
        treatment_record_uuid: UUID,
        user_uuid: str,
    ) -> None:
        record = await TreatmentRecordService.get_treatment_record(
            db, treatment_record_uuid, user_uuid
        )

        if not record.is_active:
            return

        logger.info(
            f"Arquivando prontuário: {treatment_record_uuid}",
            extra={
                "user_uuid": str(user_uuid),
                "treatment_record_uuid": str(treatment_record_uuid),
            },
        )

        old_number = record.record_number
        record.is_active = False
        record.record_number = None
        db.add(record)

        if old_number is not None:
            stmt = (
                update(TreatmentRecord)
                .where(
                    TreatmentRecord.treatment_uuid == record.treatment_uuid,
                    TreatmentRecord.is_active,
                    TreatmentRecord.record_number > old_number,
                )
                .values(record_number=TreatmentRecord.record_number - 1)
            )
            await db.execute(stmt)

        await db.commit()

    @staticmethod
    async def _trigger_context_update_if_needed(
        record: TreatmentRecord, user_uuid: str
    ):
        from src.models.treatment_record_model import RecordStatus  # noqa: PLC0415, I001

        if (
            record.status == RecordStatus.READY
            and record.content
            and record.content not in SYSTEM_PLACEHOLDERS
        ):
            from src.tasks.context_update import (  # noqa: PLC0415
                generate_context_draft_task,
            )

            logger.info(
                f"Disparando atualização de contexto para o prontuário {record.uuid}"  # noqa: E501
            )
            generate_context_draft_task.delay(
                treatment_uuid=str(record.treatment_uuid),
                treatment_record_uuid=str(record.uuid),
                user_uuid=str(user_uuid),
            )
