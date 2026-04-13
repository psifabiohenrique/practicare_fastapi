import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.automated_report_service import AutomatedReportService
from src.models.treatment_report_model import ReportType

@pytest.mark.asyncio
@patch("src.services.automated_report_service.AutomatedReportService._get_first_record_date")
async def test_resolve_date_range_completo(mock_get_first, mock_db):
    mock_get_first.return_value = date(2023, 1, 1)
    job = MagicMock()
    today = date.today()
    start, end, inc = await AutomatedReportService._resolve_date_range(mock_db, job, ReportType.COMPLETO, today)
    assert start == date(2023, 1, 1)
    assert end == today
    assert inc is True

@pytest.mark.asyncio
@patch("src.services.automated_report_service.TreatmentReportService.get_treatment_report")
@patch("src.services.automated_report_service.AutomatedReportService._get_last_report_date")
async def test_resolve_date_range_periodico_placeholder(mock_get_last, mock_get_report, mock_db):
    today = date.today()
    mock_get_report.return_value = MagicMock(start_date_period=today, end_date_period=today)
    mock_get_last.return_value = date(2023, 1, 1)
    job = MagicMock()
    start, end, inc = await AutomatedReportService._resolve_date_range(mock_db, job, ReportType.PERIODICO, today)
    assert start == date(2023, 1, 1)
    assert end == today
    assert inc is True

@pytest.mark.asyncio
@patch("src.services.automated_report_service.TreatmentReportService.get_treatment_report")
async def test_resolve_date_range_periodico_not_placeholder(mock_get_report, mock_db):
    today = date.today()
    provided_start = today - timedelta(days=10)
    provided_end = today - timedelta(days=5)
    mock_get_report.return_value = MagicMock(start_date_period=provided_start, end_date_period=provided_end)
    job = MagicMock()
    start, end, inc = await AutomatedReportService._resolve_date_range(mock_db, job, ReportType.PERIODICO, today)
    assert start == provided_start
    assert end == provided_end
    assert inc is True

@pytest.mark.asyncio
@patch("src.services.automated_report_service.TreatmentReportService.get_treatment_report")
@patch("src.services.automated_report_service.AutomatedReportService._get_first_record_date")
async def test_resolve_date_range_focado_placeholder(mock_get_first, mock_get_report, mock_db):
    today = date.today()
    mock_get_report.return_value = MagicMock(start_date_period=today, end_date_period=today)
    mock_get_first.return_value = date(2023, 1, 1)
    job = MagicMock()
    start, end, inc = await AutomatedReportService._resolve_date_range(mock_db, job, ReportType.FOCADO, today)
    assert start == date(2023, 1, 1)
    assert end == today
    assert inc is True

@pytest.mark.asyncio
@patch("src.services.automated_report_service.TreatmentReportService.get_treatment_report")
async def test_resolve_date_range_focado_not_placeholder(mock_get_report, mock_db):
    today = date.today()
    provided_start = today - timedelta(days=10)
    provided_end = today - timedelta(days=5)
    mock_get_report.return_value = MagicMock(start_date_period=provided_start, end_date_period=provided_end)
    job = MagicMock()
    start, end, inc = await AutomatedReportService._resolve_date_range(mock_db, job, ReportType.FOCADO, today)
    assert start == provided_start
    assert end == provided_end
    assert inc is True

@pytest.mark.asyncio
async def test_get_first_record_date(mock_db):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = date(2023, 1, 1)
    mock_db.execute.return_value = mock_result
    d = await AutomatedReportService._get_first_record_date(mock_db, "t-uuid")
    assert d == date(2023, 1, 1)

@pytest.mark.asyncio
async def test_get_first_record_date_none(mock_db):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    d = await AutomatedReportService._get_first_record_date(mock_db, "t-uuid")
    assert d == date.today()

@pytest.mark.asyncio
async def test_get_last_report_date(mock_db):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = date(2023, 2, 1)
    mock_db.execute.return_value = mock_result
    d = await AutomatedReportService._get_last_report_date(mock_db, "t-uuid", "r-uuid")
    assert d == date(2023, 2, 1)

@pytest.mark.asyncio
async def test_get_last_report_date_none(mock_db):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    d = await AutomatedReportService._get_last_report_date(mock_db, "t-uuid", "r-uuid")
    assert d == date.today() - timedelta(days=30)

@pytest.mark.asyncio
async def test_get_treatment_context(mock_db, mock_context):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_context
    mock_db.execute.return_value = mock_result
    ctx = await AutomatedReportService._get_treatment_context(mock_db, "t-uuid")
    assert ctx == mock_context

def test_format_treatment_context_none():
    assert AutomatedReportService._format_treatment_context(None) is None

def test_format_treatment_context_full(mock_context):
    mock_context.clinical_history = "H"
    mock_context.psychological_patterns = "P"
    mock_context.therapeutic_goals = "G"
    mock_context.life_dynamics = "D"
    mock_context.medication_notes = "M"
    res = AutomatedReportService._format_treatment_context(mock_context)
    assert "Histórico Clínico" in res
    assert "Padrões Psicológicos" in res
    assert "Objetivos Terapêuticos" in res
    assert "Dinâmicas de Vida" in res
    assert "Notas de Medicação" in res

def test_format_treatment_context_empty(mock_context):
    mock_context.clinical_history = None
    mock_context.psychological_patterns = None
    mock_context.therapeutic_goals = None
    mock_context.life_dynamics = None
    mock_context.medication_notes = None
    assert AutomatedReportService._format_treatment_context(mock_context) is None
