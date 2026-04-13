from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.ai.ai_result import AIResult
from src.core.exceptions import NotFoundError
from src.models.automated_report_job import AutomatedReportJob, ReportJobStatus
from src.models.treatment_report_model import ReportType
from src.services.automated_report_service import AutomatedReportService
from datetime import date


@pytest.fixture
def mock_job():
    job = MagicMock(spec=AutomatedReportJob)
    job.uuid = uuid4()
    job.user_uuid = uuid4()
    job.treatment_uuid = uuid4()
    job.treatment_report_uuid = uuid4()
    job.status = ReportJobStatus.PENDING
    job.error_message = None
    return job


class TestAutomatedReportServiceLifecycle:
    @pytest.mark.asyncio
    async def test_create_job(self, mock_db):
        treatment_uuid = uuid4()
        report_uuid = uuid4()
        user_uuid = uuid4()

        job = await AutomatedReportService.create_job(
            mock_db, treatment_uuid, report_uuid, user_uuid
        )

        assert isinstance(job, AutomatedReportJob)
        assert job.user_uuid == user_uuid
        assert job.treatment_uuid == str(treatment_uuid)
        assert job.treatment_report_uuid == str(report_uuid)
        assert job.status == ReportJobStatus.PENDING
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_job_success(self, mock_db, mock_job):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_job
        mock_db.execute.return_value = result_mock

        job = await AutomatedReportService.get_job(mock_db, mock_job.uuid)

        assert job == mock_job

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, mock_db):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        with pytest.raises(NotFoundError, match="Job not found"):
            await AutomatedReportService.get_job(mock_db, uuid4())

    @pytest.mark.asyncio
    async def test_update_job_status(self, mock_db, mock_job):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_job
        mock_db.execute.return_value = result_mock

        await AutomatedReportService.update_job_status(
            mock_db, mock_job.uuid, ReportJobStatus.COMPLETED, "Some error"
        )

        assert mock_job.status == ReportJobStatus.COMPLETED
        assert mock_job.error_message == "Some error"
        mock_db.commit.assert_called_once()


class TestAutomatedReportServiceProcessing:
    @pytest.mark.asyncio
    @patch(
        "src.services.automated_report_service.AutomatedReportService.get_job"
    )
    @patch(
        "src.services.automated_report_service.AutomatedReportService.update_job_status"
    )
    @patch(
        "src.services.automated_report_service.AutomatedReportService.generate_report_content"
    )
    async def test_process_automated_report_job_success(
        self,
        mock_generate,
        mock_update_status,
        mock_get_job,
        mock_db,
        mock_job,
    ):
        mock_get_job.return_value = mock_job

        await AutomatedReportService.process_automated_report_job(
            mock_db, mock_job.uuid
        )

        assert mock_update_status.call_count == 2
        mock_generate.assert_called_once_with(mock_db, mock_job)

    @pytest.mark.asyncio
    @patch(
        "src.services.automated_report_service.AutomatedReportService.get_job"
    )
    @patch(
        "src.services.automated_report_service.AutomatedReportService.update_job_status"
    )
    @patch(
        "src.services.automated_report_service.AutomatedReportService.generate_report_content"
    )
    @patch(
        "src.services.automated_report_service.TreatmentReportService.update_treatment_report"
    )
    async def test_process_automated_report_job_failure(  # noqa: PLR0917
        self,
        mock_update_report,
        mock_generate,
        mock_update_status,
        mock_get_job,
        mock_db,
        mock_job,
    ):
        mock_get_job.return_value = mock_job
        mock_generate.side_effect = Exception("Generation failed")

        await AutomatedReportService.process_automated_report_job(
            mock_db, mock_job.uuid
        )

        # 1. Update status to GENERATING_REPORT
        # 2. Update status to FAILED
        assert mock_update_status.call_count == 2
        mock_update_status.assert_any_call(
            mock_db,
            mock_job.uuid,
            ReportJobStatus.FAILED,
            error_message="Generation failed",
        )
        mock_update_report.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.services.automated_report_service.UsageStatisticService")
    @patch(
        "src.services.automated_report_service.PatientWithTreatmentService.get_patient_with_treatment_uuid"
    )
    @patch(
        "src.services.automated_report_service.TreatmentReportService.get_treatment_report"
    )
    @patch(
        "src.services.automated_report_service.TreatmentRecordService.get_treatment_records"
    )
    @patch("src.services.automated_report_service.ReportGenerationChain")
    @patch(
        "src.services.automated_report_service.TreatmentReportService.update_treatment_report"
    )
    async def test_generate_report_content(  # noqa: PLR0917
        self,
        mock_update_report,
        MockChain,
        mock_get_records,
        mock_get_report,
        mock_get_patient,
        mock_usage_service,
        mock_db,
        mock_job,
    ):
        # Mock patient
        patient = MagicMock()
        patient.first_name = "Jane Doe"
        patient.gender = "Female"
        mock_get_patient.return_value = patient

        # Mock current report
        current_report = MagicMock()
        current_report.report_type = ReportType.PERIODICO
        current_report.start_date_period = date(2023, 1, 1)
        current_report.end_date_period = date(2023, 1, 31)
        current_report.system_prompt = None
        mock_get_report.return_value = current_report

        # Mock TreatmentContext query
        treatment_context = MagicMock()
        treatment_context.clinical_history = "clinical history"
        treatment_context.psychological_patterns = ""
        treatment_context.therapeutic_goals = ""
        treatment_context.life_dynamics = ""
        treatment_context.medication_notes = ""

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.side_effect = [treatment_context]
        mock_db.execute.return_value = result_mock

        # Mock records
        record = MagicMock()
        record.date = "2023-01-15"
        record.content = "Session content"
        mock_get_records.return_value = [record]

        mock_usage_service.create_statistic = AsyncMock()

        # Mock AI Chain
        chain_instance = MockChain.return_value
        chain_instance.generate = AsyncMock()
        report_data = MagicMock()
        report_data.demand_description = "new demand"
        report_data.procedures = "new procs"
        report_data.analysis = "new anal"
        report_data.conclusion = "new conc"
        chain_instance.generate.return_value = AIResult(
            content=report_data, input_tokens=50, output_tokens=50
        )

        result = await AutomatedReportService.generate_report_content(
            mock_db, mock_job
        )

        assert result == report_data
        mock_update_report.assert_called_once()
        chain_instance.generate.assert_called_once()
        mock_usage_service.create_statistic.assert_called_once()

    @pytest.mark.asyncio
    @patch(
        "src.services.automated_report_service.AutomatedReportService.get_job"
    )
    @patch(
        "src.services.automated_report_service.AutomatedReportService.update_job_status"
    )
    @patch(
        "src.services.automated_report_service.AutomatedReportService.generate_report_content"
    )
    @patch(
        "src.services.automated_report_service.TreatmentReportService.update_treatment_report"
    )
    async def test_process_automated_report_job_double_failure(  # noqa: PLR0917
        self,
        mock_update_report,
        mock_generate,
        mock_update_status,
        mock_get_job,
        mock_db,
        mock_job,
    ):
        mock_get_job.return_value = mock_job
        mock_generate.side_effect = Exception("First failure")
        mock_update_report.side_effect = Exception("Second failure")

        # This should not raise because of the internal try-except
        await AutomatedReportService.process_automated_report_job(
            mock_db, mock_job.uuid
        )

        mock_update_status.assert_any_call(
            mock_db,
            mock_job.uuid,
            ReportJobStatus.FAILED,
            error_message="First failure",
        )

    @pytest.mark.asyncio
    @patch("src.services.automated_report_service.UsageStatisticService")
    @patch(
        "src.services.automated_report_service.PatientWithTreatmentService.get_patient_with_treatment_uuid"
    )
    @patch(
        "src.services.automated_report_service.TreatmentReportService.get_treatment_report"
    )
    @patch(
        "src.services.automated_report_service.TreatmentRecordService.get_treatment_records"
    )
    @patch("src.services.automated_report_service.ReportGenerationChain")
    @patch(
        "src.services.automated_report_service.TreatmentReportService.update_treatment_report"
    )
    async def test_generate_report_content_no_prev_no_records(  # noqa: PLR0917
        self,
        mock_update_report,
        MockChain,
        mock_get_records,
        mock_get_report,
        mock_get_patient,
        mock_usage_service,
        mock_db,
        mock_job,
    ):
        # Mock patient
        patient = MagicMock()
        patient.first_name = "Jane"
        patient.gender = "Female"
        mock_get_patient.return_value = patient

        # Mock current report
        current_report = MagicMock()
        current_report.report_type = ReportType.PERIODICO
        current_report.start_date_period = date(2023, 1, 1)
        current_report.end_date_period = date(2023, 1, 31)
        current_report.system_prompt = None
        mock_get_report.return_value = current_report

        # Mock previous report query (None)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        # Mock records (Empty)
        mock_get_records.return_value = []

        mock_usage_service.create_statistic = AsyncMock()

        # Mock AI Chain return value properly with strings
        report_data = MagicMock()
        report_data.demand_description = "demand"
        report_data.procedures = "procs"
        report_data.analysis = "anal"
        report_data.conclusion = "conc"

        chain_instance = MockChain.return_value
        chain_instance.generate = AsyncMock()
        chain_instance.generate.return_value = AIResult(
            content=report_data, input_tokens=1, output_tokens=1
        )

        await AutomatedReportService.generate_report_content(mock_db, mock_job)

        chain_instance.generate.assert_called_once()
        mock_usage_service.create_statistic.assert_called_once()
        # Verify context strings passed to AI
        args, kwargs = chain_instance.generate.call_args
        assert kwargs["treatment_context"] is None
        assert (
            kwargs["records_context"]
            == "Nenhum prontuário encontrado para este período."
        )

    @pytest.mark.asyncio
    @patch("src.services.automated_report_service.UsageStatisticService")
    @patch(
        "src.services.automated_report_service.PatientWithTreatmentService.get_patient_with_treatment_uuid"
    )
    @patch(
        "src.services.automated_report_service.TreatmentReportService.get_treatment_report"
    )
    @patch(
        "src.services.automated_report_service.TreatmentRecordService.get_treatment_records"
    )
    @patch("src.services.automated_report_service.ReportGenerationChain")
    @patch(
        "src.services.automated_report_service.TreatmentReportService.update_treatment_report"
    )
    @patch("src.services.automated_report_service.AutomatedReportService._get_first_record_date")
    @patch("src.services.automated_report_service.AutomatedReportService._get_treatment_context")
    async def test_generate_report_content_completo(  # noqa: PLR0917
        self,
        mock_get_ctx,
        mock_get_first_date,
        mock_update_report,
        MockChain,
        mock_get_records,
        mock_get_report,
        mock_get_patient,
        mock_usage_service,
        mock_db,
        mock_job,
    ):
        mock_get_patient.return_value = MagicMock(first_name="John", gender="Male")
        mock_get_report.return_value = MagicMock(report_type=ReportType.COMPLETO, system_prompt=None)
        mock_get_first_date.return_value = date(2023, 1, 1)
        mock_get_records.return_value = []
        mock_get_ctx.return_value = MagicMock(clinical_history="History")
        
        mock_usage_service.create_statistic = AsyncMock()
        chain_instance = MockChain.return_value
        report_data = MagicMock()
        report_data.demand_description = "demand"
        report_data.procedures = "procedures"
        report_data.analysis = "analysis"
        report_data.conclusion = "conclusion"
        chain_instance.generate = AsyncMock(return_value=AIResult(content=report_data, input_tokens=1, output_tokens=1))
        
        await AutomatedReportService.generate_report_content(mock_db, mock_job)
        
        mock_get_ctx.assert_called_once()
        chain_instance.generate.assert_called_once()
        _, kwargs = chain_instance.generate.call_args
        assert "Histórico Clínico:\nHistory" in kwargs["treatment_context"]
