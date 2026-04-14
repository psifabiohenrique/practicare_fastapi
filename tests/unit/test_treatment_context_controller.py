import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from fastapi import status
from src.routers.treatment_context_controller import (
    get_context_with_draft,
    update_context,
    apply_draft,
    reject_draft,
    generate_context,
)
from src.schemas.treatment_context_schema import (
    TreatmentContextUpdate,
    TreatmentContextApplyDraft,
    TreatmentContextGenerate,
)

@pytest.mark.asyncio
@patch("src.routers.treatment_context_controller.TreatmentContextService.get_context_with_pending_draft")
async def test_get_context_with_draft(mock_service, mock_db, mock_user):
    mock_service.return_value = (MagicMock(), MagicMock())
    res = await get_context_with_draft(uuid4(), mock_db, mock_user)
    assert "context" in res
    assert "pending_draft" in res

@pytest.mark.asyncio
@patch("src.routers.treatment_context_controller.TreatmentContextService.update_context")
async def test_update_context(mock_service, mock_db, mock_user):
    mock_service.return_value = MagicMock()
    schema = TreatmentContextUpdate(life_dynamics=["new"])
    res = await update_context(uuid4(), schema, mock_db, mock_user)
    assert res is not None

@pytest.mark.asyncio
@patch("src.routers.treatment_context_controller.TreatmentContextService.apply_draft")
async def test_apply_draft(mock_service, mock_db, mock_user):
    mock_service.return_value = MagicMock()
    schema = TreatmentContextApplyDraft(life_dynamics=["final"])
    res = await apply_draft(uuid4(), schema, mock_db, mock_user)
    assert res is not None

@pytest.mark.asyncio
@patch("src.routers.treatment_context_controller.TreatmentContextService.reject_draft")
async def test_reject_draft(mock_service, mock_db, mock_user):
    mock_service.return_value = None
    await reject_draft(uuid4(), mock_db, mock_user)
    mock_service.assert_called_once()

@pytest.mark.asyncio
@patch("src.routers.treatment_context_controller.TreatmentContextService.schedule_context_generation")
async def test_generate_context(mock_service, mock_db, mock_user):
    mock_service.return_value = MagicMock()
    schema = TreatmentContextGenerate(historical_notes="notes", include_existing_records=True)
    res = await generate_context(uuid4(), schema, mock_db, mock_user)
    assert res is not None
