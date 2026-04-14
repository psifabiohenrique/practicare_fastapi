import json
import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.ai.chains.context_generation import ContextGenerationChain, extract_json as extract_json_gen
from src.ai.chains.context_update import ContextUpdateChain, extract_json as extract_json_upd
from src.ai.ai_result import AIResult
from src.ai.exceptions import AIFatalError, AITransientError

def test_extract_json():
    # Test both identical functions to ensure coverage
    for fn in [extract_json_gen, extract_json_upd]:
        assert fn("```json\n{\"a\": 1}\n```") == "{\"a\": 1}"
        assert fn("```\n{\"a\": 1}\n```") == "{\"a\": 1}"
        assert fn("plain") == "plain"

class TestContextGenerationChain:
    def test_unsupported_provider(self):
        with pytest.raises(ValueError, match="Provider unknown not supported"):
            ContextGenerationChain(provider="unknown")

    @pytest.mark.asyncio
    @patch("src.ai.chains.context_generation.AsyncOpenAI")
    async def test_generate_openai_success(self, mock_openai):
        mock_client = mock_openai.return_value
        mock_resp = MagicMock()
        mock_resp.usage.prompt_tokens = 10
        mock_resp.usage.completion_tokens = 20
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = json.dumps({"life_dynamics": ["test"]})
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        
        chain = ContextGenerationChain(provider="openai")
        result = await chain.generate("material", "male")
        
        assert isinstance(result, AIResult)
        assert result.content["life_dynamics"] == ["test"]

    @pytest.mark.asyncio
    @patch("src.ai.chains.context_generation.genai.Client")
    async def test_generate_google_success(self, mock_genai):
        mock_client = mock_genai.return_value
        mock_resp = MagicMock()
        mock_resp.text = json.dumps({"life_dynamics": ["test"]})
        mock_client.models.generate_content.return_value = mock_resp
        
        chain = ContextGenerationChain(provider="google")
        result = await chain.generate("material", "male")
        
        assert isinstance(result, AIResult)
        # Google provider returns a validated dict or model depending on implementation
        # But here it's likely a dict after json.loads or Pydantic validation

    @pytest.mark.asyncio
    @patch("src.ai.chains.context_generation.AsyncOpenAI")
    async def test_generate_openai_network_error(self, mock_openai):
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create.side_effect = httpx.ConnectError("fail")
        
        chain = ContextGenerationChain(provider="openai")
        with pytest.raises(AITransientError):
            await chain.generate("m", "g")

    @pytest.mark.asyncio
    @patch("src.ai.chains.context_generation.AsyncOpenAI")
    async def test_generate_openai_transient_error(self, mock_openai):
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create.side_effect = Exception("429 Rate limit exceeded")
        chain = ContextGenerationChain(provider="openai")
        with pytest.raises(AITransientError):
            await chain.generate("m", "g")

    @pytest.mark.asyncio
    @patch("src.ai.chains.context_generation.AsyncOpenAI")
    async def test_generate_openai_fatal_error(self, mock_openai):
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create.side_effect = Exception("403 Forbidden")
        chain = ContextGenerationChain(provider="openai")
        with pytest.raises(AIFatalError):
            await chain.generate("m", "g")

    @pytest.mark.asyncio
    @patch("src.ai.chains.context_generation.AsyncOpenAI")
    async def test_generate_openai_unknown_error(self, mock_openai):
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create.side_effect = Exception("Strange thing")
        chain = ContextGenerationChain(provider="openai")
        with pytest.raises(AIFatalError, match="Erro desconhecido"):
            await chain.generate("m", "g")

    @pytest.mark.asyncio
    @patch("src.ai.chains.context_generation.AsyncOpenAI")
    async def test_generate_openai_string_fallback(self, mock_openai):
        mock_client = mock_openai.return_value
        mock_resp = MagicMock()
        mock_resp.usage.prompt_tokens = 10
        mock_resp.usage.completion_tokens = 20
        mock_resp.choices = [MagicMock()]
        # AI returns a string instead of a list for clinical_history
        mock_resp.choices[0].message.content = json.dumps({
            "clinical_history": "- line 1\n- line 2",
            "life_dynamics": ["test"]
        })
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        
        chain = ContextGenerationChain(provider="openai")
        result = await chain.generate("material", "male")
        
        assert result.content["clinical_history"] == ["line 1", "line 2"]
        assert result.content["life_dynamics"] == ["test"]

    @pytest.mark.asyncio
    @patch("src.ai.chains.context_generation.AsyncOpenAI")
    async def test_generate_openai_invalid_type_fallback(self, mock_openai):
        mock_client = mock_openai.return_value
        mock_resp = MagicMock()
        mock_resp.usage.prompt_tokens = 10
        mock_resp.usage.completion_tokens = 20
        mock_resp.choices = [MagicMock()]
        # AI returns an integer instead of a list/string for clinical_history
        mock_resp.choices[0].message.content = json.dumps({
            "clinical_history": 123,
            "life_dynamics": ["test"]
        })
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        
        chain = ContextGenerationChain(provider="openai")
        result = await chain.generate("material", "male")
        
        assert result.content["clinical_history"] is None
        assert result.content["life_dynamics"] == ["test"]

class TestContextUpdateChain:


    def test_unsupported_provider(self):
        with pytest.raises(ValueError, match="Provider unknown not supported"):
            ContextUpdateChain(provider="unknown")

    @pytest.mark.asyncio
    @patch("src.ai.chains.context_update.AsyncOpenAI")
    async def test_generate_openai_non_list_context(self, mock_openai):
        mock_client = mock_openai.return_value
        mock_resp = MagicMock()
        mock_resp.usage.prompt_tokens = 5
        mock_resp.usage.completion_tokens = 5
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = json.dumps({"clinical_history": {"add": ["updated"], "remove": []}})
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        
        chain = ContextUpdateChain(provider="openai")
        # Pass a context where life_dynamics is not a list
        result = await chain.generate({"life_dynamics": "Not a list"}, "new record", "male")
        
        assert result.content["clinical_history"] == {"add": ["updated"], "remove": []}

    def test_parse_draft_response_non_dict_val(self):
        from src.ai.chains.context_update import parse_draft_response
        # AI returns a string instead of a dict for a field
        raw = {"clinical_history": "Not a dict"}
        result = parse_draft_response(raw)
        assert result["clinical_history"] is None

    @pytest.mark.asyncio
    @patch("src.ai.chains.context_update.AsyncOpenAI")
    async def test_generate_openai_success(self, mock_openai):
        mock_client = mock_openai.return_value
        mock_resp = MagicMock()
        mock_resp.usage.prompt_tokens = 5
        mock_resp.usage.completion_tokens = 5
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = json.dumps({"clinical_history": {"add": ["updated"], "remove": []}})
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
        
        chain = ContextUpdateChain(provider="openai")
        result = await chain.generate({"life_dynamics": ["bullet 1"]}, "new record", "male")
        
        assert result.content["clinical_history"] == {"add": ["updated"], "remove": []}

    @pytest.mark.asyncio
    @patch("src.ai.chains.context_update.genai.Client")
    async def test_generate_google_success(self, mock_genai):
        mock_client = mock_genai.return_value
        mock_resp = MagicMock()
        mock_resp.text = json.dumps({"clinical_history": {"add": ["updated"], "remove": []}})
        mock_client.models.generate_content.return_value = mock_resp
        
        chain = ContextUpdateChain(provider="google")
        result = await chain.generate({"old": "context"}, "new record", "male")
        assert result is not None

    @pytest.mark.asyncio
    @patch("src.ai.chains.context_update.AsyncOpenAI")
    async def test_generate_openai_transient_error(self, mock_openai):
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create.side_effect = Exception("429 rate limit")
        chain = ContextUpdateChain(provider="openai")
        with pytest.raises(AITransientError):
            await chain.generate({"o": "c"}, "r", "m")

    @pytest.mark.asyncio
    @patch("src.ai.chains.context_update.AsyncOpenAI")
    async def test_generate_openai_fatal_error(self, mock_openai):
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create.side_effect = Exception("401 unauthorized")
        chain = ContextUpdateChain(provider="openai")
        with pytest.raises(AIFatalError):
            await chain.generate({"o": "c"}, "r", "m")

    @pytest.mark.asyncio
    @patch("src.ai.chains.context_update.AsyncOpenAI")
    async def test_generate_openai_network_error(self, mock_openai):
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create.side_effect = httpx.ConnectError("fail")
        chain = ContextUpdateChain(provider="openai")
        with pytest.raises(AITransientError):
            await chain.generate({"o": "c"}, "r", "m")

    @pytest.mark.asyncio
    @patch("src.ai.chains.context_update.AsyncOpenAI")
    async def test_generate_openai_unknown_error(self, mock_openai):
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create.side_effect = Exception("Strange thing")
        chain = ContextUpdateChain(provider="openai")
        with pytest.raises(AIFatalError, match="Erro desconhecido"):
            await chain.generate({"o": "c"}, "r", "m")
