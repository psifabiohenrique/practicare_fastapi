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

class TestContextUpdateChain:
    def test_unsupported_provider(self):
        with pytest.raises(ValueError, match="Provider unknown not supported"):
            ContextUpdateChain(provider="unknown")

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
        result = await chain.generate({"old": "context"}, "new record", "male")
        
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
