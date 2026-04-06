import logging
from datetime import date
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, status

from src.routers.deps import CurrentUser, SessionDB
from src.schemas.treatment_report_schema import (
    AutomatedReportCreate,
    ReportStatus,
    TreatmentReportCreate,
    TreatmentReportRead,
    TreatmentReportUpdate,
)
from src.services.automated_report_service import AutomatedReportService
from src.services.treatment_report_service import TreatmentReportService
from src.tasks.report_generation import generate_report_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/treatment-reports", tags=["Treatment reports"])


@router.get(
    "/treatment/{treatment_uuid}", response_model=list[TreatmentReportRead]
)
async def list_treatment_reports(
    treatment_uuid: UUID,
    db: SessionDB,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> any:
    return await TreatmentReportService.get_treatment_reports(
        db, treatment_uuid, current_user.uuid, skip, limit
    )


@router.get("/{treatment_report_uuid}", response_model=TreatmentReportRead)
async def get_treatment_report(
    treatment_report_uuid: UUID,
    db: SessionDB,
    current_user: CurrentUser,
) -> any:
    return await TreatmentReportService.get_treatment_report(
        db, treatment_report_uuid, current_user.uuid
    )


@router.post(
    "",
    response_model=TreatmentReportRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_treatment_report(
    schema: TreatmentReportCreate,
    db: SessionDB,
    current_user: CurrentUser,
) -> any:
    logger.info(
        "Criando relatório de tratamento. Usuário: %s, Tratamento: %s",
        current_user.uuid,
        schema.treatment_uuid,
        extra={
            "user_uuid": str(current_user.uuid),
            "treatment_uuid": str(schema.treatment_uuid),
        },
    )
    return await TreatmentReportService.create_treatment_report(
        db, schema, current_user.uuid
    )


@router.patch("/{treatment_report_uuid}", response_model=TreatmentReportRead)
async def update_treatment_report(
    treatment_report_uuid: UUID,
    schema: TreatmentReportUpdate,
    db: SessionDB,
    current_user: CurrentUser,
) -> any:
    logger.info(
        f"Atualizando relatório de tratamento: {treatment_report_uuid}",
        extra={
            "user_uuid": str(current_user.uuid),
            "treatment_report_uuid": str(treatment_report_uuid),
        },
    )
    return await TreatmentReportService.update_treatment_report(
        db, treatment_report_uuid, current_user.uuid, schema
    )


@router.delete(
    "/{treatment_report_uuid}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_treatment_report(
    treatment_report_uuid: UUID,
    db: SessionDB,
    current_user: CurrentUser,
) -> None:
    logger.info(
        f"Deletando relatório de tratamento: {treatment_report_uuid}",
        extra={
            "user_uuid": str(current_user.uuid),
            "treatment_report_uuid": str(treatment_report_uuid),
        },
    )
    await TreatmentReportService.delete_treatment_report(
        db, treatment_report_uuid, current_user.uuid
    )


@router.post(
    "/treatments/{treatment_uuid}/automated-report",
    response_model=TreatmentReportRead,
)
async def create_automated_report(
    treatment_uuid: UUID,
    schema: AutomatedReportCreate,
    db: SessionDB,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
) -> any:
    user_uuid = current_user.uuid
    today = date.today()

    logger.info(
        "Solicitação de relatório automatizado recebida. "
        "Tratamento: %s, Tipo: %s",
        treatment_uuid,
        schema.report_type,
        extra={
            "user_uuid": str(user_uuid),
            "treatment_uuid": str(treatment_uuid),
            "report_type": schema.report_type,
        },
    )

    # Determine placeholder dates — the service will overwrite them
    # with the real calculated values after generation.
    # For PERIODICO and FOCADO, if the user provided dates, we use them;
    # otherwise we use today as a placeholder so NOT NULL is satisfied.
    start_placeholder = schema.start_date_period or today
    end_placeholder = schema.end_date_period or today

    # 1. Create report with PROCESSING status and placeholder dates
    report = await TreatmentReportService.create_treatment_report(
        db=db,
        schema=TreatmentReportCreate(
            treatment_uuid=treatment_uuid,
            demand_description="Processando em background...",
            procedures="Processando em background...",
            analysis="Processando em background...",
            conclusion="Processando em background...",
            issue_date=today,
            start_date_period=start_placeholder,
            end_date_period=end_placeholder,
            status=ReportStatus.PROCESSING,
            report_type=schema.report_type,
            system_prompt=schema.system_prompt,
        ),
        user_uuid=user_uuid,
    )

    # 2. Create the background job
    job = await AutomatedReportService.create_job(
        db=db,
        treatment_uuid=treatment_uuid,
        treatment_report_uuid=report.uuid,
        user_uuid=user_uuid,
    )

    logger.info(
        f"Job de relatório automatizado criado: {job.uuid}. Disparando task.",
        extra={"job_uuid": str(job.uuid), "report_uuid": str(report.uuid)},
    )
    generate_report_task.delay(job_uuid=job.uuid)

    return report
