from uuid import UUID

from fastapi import APIRouter, status

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
    "/",
    response_model=TreatmentReportRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_treatment_report(
    schema: TreatmentReportCreate,
    db: SessionDB,
    current_user: CurrentUser,
) -> any:
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
    return await TreatmentReportService.update_treatment_report(
        db, treatment_report_uuid, current_user.uuid, schema
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
) -> any:
    user_uuid = current_user.uuid

    # 1. Inicializar o relatório com status PROCESSING e conteúdo temporário
    report = await TreatmentReportService.create_treatment_report(
        db=db,
        schema=TreatmentReportCreate(
            treatment_uuid=treatment_uuid,
            demand_description="Processando em background...",
            procedures="Processando em background...",
            analysis="Processando em background...",
            conclusion="Processando em background...",
            issue_date=schema.issue_date,
            start_date_period=schema.start_date_period,
            end_date_period=schema.end_date_period,
            status=ReportStatus.PROCESSING,
        ),
        user_uuid=user_uuid,
    )

    # 2. Criar o job
    job = await AutomatedReportService.create_job(
        db=db,
        treatment_uuid=treatment_uuid,
        treatment_report_uuid=UUID(report.uuid),  # type: ignore
        user_uuid=user_uuid,
    )

    # 3. Disparar a task do Celery
    generate_report_task.delay(job_uuid=UUID(job.uuid))  # type: ignore

    return report
