import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from src.tasks.context_update import (
    generate_context_draft_logic,
    do_generate_context_draft,
    generate_context_draft_task,
)
from src.ai.exceptions import AIFatalError, AITransientError

@pytest.mark.asyncio
@patch("src.tasks.context_update.get_async_session")
@patch("src.tasks.context_update.TreatmentContextService.generate_context_draft")
async def test_generate_context_draft_logic_success(mock_gen_draft, mock_get_session, mock_db):
    mock_get_session.return_value = mock_db
    t_uuid = str(uuid4())
    tr_uuid = str(uuid4())
    u_uuid = "user-123"

    await generate_context_draft_logic(t_uuid, tr_uuid, u_uuid)

    mock_gen_draft.assert_called_once()
    mock_db.close.assert_called_once()

@patch("src.tasks.context_update.generate_context_draft_logic")
def test_do_generate_context_draft_success(mock_logic):
    mock_logic.return_value = None
    do_generate_context_draft("t", "tr", "u")
    mock_logic.assert_called_once()

@patch("src.tasks.context_update.generate_context_draft_logic")
def test_do_generate_context_draft_transient_error(mock_logic):
    mock_logic.side_effect = AITransientError("transient")
    with pytest.raises(AITransientError):
        do_generate_context_draft("t", "tr", "u")

@patch("src.tasks.context_update.generate_context_draft_logic")
def test_do_generate_context_draft_fatal_error(mock_logic):
    mock_logic.side_effect = AIFatalError("fatal")
    # Fatal error is caught and not re-raised according to code
    do_generate_context_draft("t", "tr", "u")

@patch("src.tasks.context_update.generate_context_draft_logic")
def test_do_generate_context_draft_unexpected_error(mock_logic):
    mock_logic.side_effect = Exception("unexpected")
    with pytest.raises(Exception, match="unexpected"):
        do_generate_context_draft("t", "tr", "u")

@patch("src.tasks.context_update.do_generate_context_draft")
def test_generate_context_draft_task(mock_do):
    generate_context_draft_task.run("t", "tr", "u")
    mock_do.assert_called_once_with("t", "tr", "u")
