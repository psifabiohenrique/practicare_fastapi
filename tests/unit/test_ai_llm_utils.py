from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from src.ai.llm.factory import LLMFactory
from src.ai.llm.response_extractor import ResponseExtractor


class TestLLMFactory:
    def test_get_llm_google(self):
        llm = LLMFactory.get_llm(provider="google", model_name="gemini-test")
        assert isinstance(llm, ChatGoogleGenerativeAI)
        assert llm.model == "gemini-test"

    def test_get_llm_openai(self):
        llm = LLMFactory.get_llm(provider="openai", model_name="gpt-test")
        assert isinstance(llm, ChatOpenAI)
        assert llm.model_name == "gpt-test"

    def test_get_llm_unsupported(self):
        err_match = "Unsupported provider: anthropic"
        with pytest.raises(ValueError, match=err_match):
            LLMFactory.get_llm(provider="anthropic")


class TestResponseExtractor:
    def test_extract_text_string(self):
        msg = AIMessage(content="Hello world")
        assert ResponseExtractor.extract_text(msg) == "Hello world"

    def test_extract_text_list(self):
        msg = AIMessage(
            content=[
                {"type": "text", "text": "Hello"},
                {"type": "text", "text": "world"},
            ]
        )
        assert ResponseExtractor.extract_text(msg) == "Hello\nworld"

    def test_extract_text_invalid_format(self):
        msg = MagicMock()
        msg.content = 123
        err_msg = "Formato de resposta inesperado do LLM"
        with pytest.raises(ValueError, match=err_msg):
            ResponseExtractor.extract_text(msg)
