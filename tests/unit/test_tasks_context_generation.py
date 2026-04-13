import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from src.tasks.context_generation import (
    generate_context_from_history_logic,
    do_generate_context_from_history,
    generate_context_from_history_task,
)
from src.ai.exceptions import AIFatalError, AITransientError

@pytest.mark.asyncio
@patch("src.tasks.context_generation.get_async_session")
@patch("src.tasks.context_generation.TreatmentContextService.generate_context_from_history")
async def test_generate_context_from_history_logic_success(mock_gen, mock_get_session, mock_db):
    mock_get_session.return_value = mock_db
    t_uuid = str(uuid4())
    u_uuid = "user-123"

    await generate_context_from_history_logic(t_uuid, u_uuid, "notes", True)

    mock_gen.assert_called_once()
    mock_db.close.assert_called_once()

@patch("src.tasks.context_generation.generate_context_from_history_logic")
def test_do_generate_context_from_history_success(mock_logic):
    mock_logic.return_value = None
    do_generate_context_from_history("t", "u", "n", True)
    mock_logic.assert_called_once()

@patch("src.tasks.context_generation.generate_context_from_history_logic")
def test_do_generate_context_from_history_transient_error(mock_logic):
    mock_logic.side_effect = AITransientError("transient")
    with pytest.raises(AITransientError):
        do_generate_context_from_history("t", "u", "n", True)

@patch("src.tasks.context_generation.generate_context_from_history_logic")
def test_do_generate_context_from_history_fatal_error(mock_logic):
    mock_logic.side_effect = AIFatalError("fatal")
    do_generate_context_from_history("t", "u", "n", True)

@patch("src.tasks.context_generation.generate_context_from_history_logic")
def test_do_generate_context_from_history_unexpected_error(mock_logic):
    mock_logic.side_effect = Exception("unexpected")
    with pytest.raises(Exception):
        do_generate_context_from_history("t", "u", "n", True)

@patch("src.tasks.context_generation.do_generate_context_from_history")
def test_generate_context_from_history_task(mock_do):
    generate_context_from_history_task.run("t", "u", "n", True)
    mock_do.assert_called_once_with("t", "u", "n", True)
