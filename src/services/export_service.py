import io
import logging
import zipfile

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.treatment_record_model import TreatmentRecord
from src.models.treatment_report_model import TreatmentReport
from src.services.patient_with_treatment_service import (
    PatientWithTreatmentService,
)

logger = logging.getLogger(__name__)


class ExportService:
    @staticmethod
    async def generate_user_backup(
        db: AsyncSession, user_uuid: str
    ) -> io.BytesIO:
        """
        Gathers all patient data for the user and generates a ZIP
        stream containing markdown files for each patient's records
        and reports.
        """
        logger.info("Generating backup for user %s", user_uuid)

        # Get all treatments connected to this user
        treatments = (
            await PatientWithTreatmentService.get_treatments_with_user_uuid(
                db=db, user_uuid=user_uuid, limit=1000
            )
        )

        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(
            zip_buffer, "a", zipfile.ZIP_DEFLATED, False
        ) as zip_file:
            for t in treatments:
                safe_name = t.patient.full_name.replace("/", "_").replace(
                    "\\", "_"
                )[:50]

                records_result = await db.execute(
                    select(TreatmentRecord)
                    .filter(
                        TreatmentRecord.treatment_uuid == str(t.uuid),
                        TreatmentRecord.is_active.is_(True),
                    )
                    .order_by(TreatmentRecord.date.asc())
                )
                records = records_result.scalars().all()

                if records:
                    records_header = (
                        f"# Prontuários do Paciente: {t.patient.full_name}\n\n"
                    )
                    records_text = records_header
                    for r in records:
                        records_text += (
                            f"## Data: {r.date.strftime('%Y-%m-%d')} | "
                            f"Horário: {r.start_time.strftime('%H:%M')} - "
                            f"{r.end_time.strftime('%H:%M')}\n\n"
                        )
                        records_text += f"{r.content}\n\n"
                        records_text += "---\n\n"

                    zip_file.writestr(
                        f"{safe_name}/Prontuários.md",
                        records_text.encode("utf-8"),
                    )

                # Fetch reports
                reports_result = await db.execute(
                    select(TreatmentReport)
                    .filter(
                        TreatmentReport.treatment_uuid == str(t.uuid),
                        TreatmentReport.is_active.is_(True),
                    )
                    .order_by(TreatmentReport.created_at.asc())
                )
                reports = reports_result.scalars().all()

                if reports:
                    reports_header = (
                        f"# Relatórios do Paciente: {t.patient.full_name}\n\n"
                    )
                    reports_text = reports_header
                    for r in reports:
                        reports_text += (
                            f"## Gerado em: "
                            f"{r.created_at.strftime('%Y-%m-%d')} | "
                            f"Tipo: {r.report_type}\n\n"
                        )
                        if r.demand_description:
                            reports_text += (
                                f"### Demanda\n{r.demand_description}\n\n"
                            )
                        if r.procedures:
                            reports_text += (
                                f"### Procedimentos\n{r.procedures}\n\n"
                            )
                        if r.analysis:
                            reports_text += (
                                f"### Análise\n{r.analysis}\n\n"
                            )
                        if r.conclusion:
                            reports_text += (
                                f"### Conclusão\n{r.conclusion}\n\n"
                            )
                        reports_text += "---\n\n"

                    zip_file.writestr(
                        f"{safe_name}/Relatórios.md",
                        reports_text.encode("utf-8"),
                    )

                # Write a patient info file just for completeness if no records/reports  # noqa: E501
                if not records and not reports:
                    zip_file.writestr(
                        f"{safe_name}/info.txt",
                        (
                            "Nenhum prontuário ou relatório encontrado "
                            f"para {t.patient.full_name}."
                        ).encode("utf-8"),
                    )

        zip_buffer.seek(0)
        return zip_buffer
