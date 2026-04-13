import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.ai.ai_result import AIResult
from src.ai.chains.record_generation import RecordGenerationChain
from src.ai.chains.report_generation import ReportGenerationChain, extract_json
from src.ai.chains.transcription import TranscriptionChain
from src.ai.exceptions import AIFatalError, AITransientError


class TestTranscriptionChain:
    @pytest.mark.asyncio
    @patch("src.ai.chains.transcription.genai.Client")
    async def test_upload_audio_success(self, mock_genai_client):
        mock_client_inst = mock_genai_client.return_value
        mock_client_inst.aio.files.upload = AsyncMock(
            return_value="file_response"
        )

        chain = TranscriptionChain()
        result = await chain.upload_audio("test.wav")

        assert result == "file_response"
        mock_client_inst.aio.files.upload.assert_called_once_with(
            file="test.wav"
        )

    @pytest.mark.asyncio
    @patch("src.ai.chains.transcription.genai.Client")
    async def test_upload_audio_failure(self, mock_genai_client):
        mock_client_inst = mock_genai_client.return_value
        mock_client_inst.aio.files.upload = AsyncMock(
            side_effect=Exception("Upload failed")
        )

        chain = TranscriptionChain()
        with pytest.raises(
            AIFatalError, match="Erro ao enviar áudio para transcrição"
        ):
            await chain.upload_audio("test.wav")

    @pytest.mark.asyncio
    @patch("src.ai.chains.transcription.genai.Client")
    async def test_upload_audio_connection_error(self, mock_genai_client):
        mock_client_inst = mock_genai_client.return_value
        mock_client_inst.aio.files.upload = AsyncMock(
            side_effect=httpx.ConnectError("Connection failed")
        )

        chain = TranscriptionChain()
        with pytest.raises(AITransientError, match="Erro de conexão ao enviar áudio"):
            await chain.upload_audio("test.wav")

    @pytest.mark.asyncio
    @patch("src.ai.chains.transcription.genai.Client")
    async def test_transcribe_success(self, mock_genai_client):
        mock_client_inst = mock_genai_client.return_value

        mock_file = MagicMock()

        # We need to mock genai.types.FileState.ACTIVE
        with patch(
            "src.ai.chains.transcription.genai.types.FileState"
        ) as mock_state:
            mock_state.ACTIVE = "ACTIVE"
            mock_file.state = "ACTIVE"
            mock_client_inst.files.get.return_value = mock_file

            mock_response = MagicMock()
            mock_response.text = "transcribed text"
            mock_client_inst.models.generate_content.return_value = (
                mock_response
            )

            chain = TranscriptionChain()
            result = await chain.transcribe("file_id")

            assert isinstance(result, AIResult)
            assert result.content == "transcribed text"
            mock_client_inst.files.get.assert_called_once_with(name="file_id")

    @pytest.mark.asyncio
    @patch("src.ai.chains.transcription.genai.Client")
    async def test_transcribe_not_ready(self, mock_genai_client):
        mock_client_inst = mock_genai_client.return_value
        mock_file = MagicMock()

        with patch(
            "src.ai.chains.transcription.genai.types.FileState"
        ) as mock_state:
            mock_state.ACTIVE = "ACTIVE"
            mock_file.state = "PROCESSING"
            mock_client_inst.files.get.return_value = mock_file

            chain = TranscriptionChain()
            with pytest.raises(
                AITransientError, match="áudio ainda não está pronto"
            ):
                await chain.transcribe("file_id")

    @pytest.mark.asyncio
    @patch("src.ai.chains.transcription.genai.Client")
    async def test_transcribe_transient_error(self, mock_genai_client):
        mock_client_inst = mock_genai_client.return_value
        mock_client_inst.files.get.side_effect = Exception(
            "429 Rate limit exceeded"
        )

        chain = TranscriptionChain()
        with pytest.raises(AITransientError, match="Erro temporário"):
            await chain.transcribe("file_id")

    @pytest.mark.asyncio
    @patch("src.ai.chains.transcription.genai.Client")
    async def test_transcribe_fatal_error(self, mock_genai_client):
        mock_client_inst = mock_genai_client.return_value
        mock_client_inst.files.get.side_effect = Exception("403 Forbidden")

        chain = TranscriptionChain()
        with pytest.raises(AIFatalError, match="Erro fatal"):
            await chain.transcribe("file_id")

    @pytest.mark.asyncio
    @patch("src.ai.chains.transcription.genai.Client")
    async def test_transcribe_unknown_error(self, mock_genai_client):
        mock_client_inst = mock_genai_client.return_value
        mock_client_inst.files.get.side_effect = Exception("Some strange bug")

        chain = TranscriptionChain()
        with pytest.raises(AIFatalError, match="Erro desconhecido"):
            await chain.transcribe("file_id")


class TestRecordGenerationChain:
    def test_unsupported_provider(self):
        with pytest.raises(ValueError, match="Provider unknown not supported"):
            RecordGenerationChain(provider="unknown")

    @pytest.mark.asyncio
    @patch("src.ai.chains.record_generation.AsyncOpenAI")
    async def test_generate_openai_success(self, mock_openai):
        mock_client = mock_openai.return_value
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = "generated record"
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)

        chain = RecordGenerationChain(provider="openai")
        result = await chain.generate("transcription", "male", "context")

        assert isinstance(result, AIResult)
        assert result.content == "generated record"

    @pytest.mark.asyncio
    @patch("src.ai.chains.record_generation.genai.Client")
    async def test_generate_google_success(self, mock_genai):
        mock_client = mock_genai.return_value
        mock_resp = MagicMock()
        mock_resp.text = "generated record"
        mock_client.models.generate_content.return_value = mock_resp

        chain = RecordGenerationChain(provider="google")
        result = await chain.generate("transcription", "male", "context")

        assert isinstance(result, AIResult)
        assert result.content == "generated record"

    @pytest.mark.asyncio
    @patch("src.ai.chains.record_generation.AsyncOpenAI")
    async def test_generate_error_mapping_transient(self, mock_openai):
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("500 Internal Error")
        )

        chain = RecordGenerationChain(provider="openai")
        with pytest.raises(AITransientError, match="Erro temporário"):
            await chain.generate("t", "m", "c")

    @pytest.mark.asyncio
    @patch("src.ai.chains.record_generation.AsyncOpenAI")
    async def test_generate_error_mapping_fatal(self, mock_openai):
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("400 Bad Request")
        )

        chain = RecordGenerationChain(provider="openai")
        with pytest.raises(AIFatalError, match="Erro fatal ocorrido"):
            await chain.generate("t", "m", "c")

    @pytest.mark.asyncio
    @patch("src.ai.chains.record_generation.AsyncOpenAI")
    async def test_generate_error_mapping_unknown(self, mock_openai):
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("Strange error")
        )

        chain = RecordGenerationChain(provider="openai")
        with pytest.raises(AIFatalError, match="Erro desconhecido"):
            await chain.generate("t", "m", "c")


class TestReportGenerationChain:
    def test_unsupported_provider(self):
        with pytest.raises(ValueError, match="Provider unknown not supported"):
            ReportGenerationChain(provider="unknown")

    def test_extract_json(self):
        text = '```json\n{"key": "val"}\n```'
        assert extract_json(text) == '{"key": "val"}'
        assert extract_json("plain text") == "plain text"

    @pytest.mark.asyncio
    @patch("src.ai.chains.report_generation.AsyncOpenAI")
    async def test_generate_openai_success(self, mock_openai):
        mock_client = mock_openai.return_value
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        report_data = {
            "demand_description": "d",
            "procedures": "p",
            "analysis": "a",
            "conclusion": "c",
        }
        mock_resp.choices[0].message.content = json.dumps(report_data)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)

        chain = ReportGenerationChain(provider="openai")
        result = await chain.generate("John", "male", "prev", "recs", custom_system_prompt="My custom instruction")

        assert isinstance(result, AIResult)
        assert result.content == report_data
        # Verify custom_system_prompt was passed to OpenAI
        _, kwargs = mock_client.chat.completions.create.call_args
        assert "[Instrução Específica do Usuário]" in kwargs["messages"][0]["content"]
        assert "My custom instruction" in kwargs["messages"][0]["content"]

    @pytest.mark.asyncio
    @patch("src.ai.chains.report_generation.genai.Client")
    async def test_generate_google_success(self, mock_genai):
        mock_client = mock_genai.return_value
        mock_resp = MagicMock()
        report_data = {
            "demand_description": "d",
            "procedures": "p",
            "analysis": "a",
            "conclusion": "c",
        }
        mock_resp.text = json.dumps(report_data)
        mock_client.models.generate_content.return_value = mock_resp

        chain = ReportGenerationChain(provider="google")
        result = await chain.generate("John", "male", "prev", "recs")

        # Google provider uses Pydantic validation and returns a Pydantic model
        assert isinstance(result, AIResult)
        assert result.content.demand_description == "d"

    @pytest.mark.asyncio
    @patch("src.ai.chains.report_generation.AsyncOpenAI")
    async def test_generate_network_error(self, mock_openai):
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create = AsyncMock(
            side_effect=httpx.ConnectError("Connection failed")
        )

        chain = ReportGenerationChain(provider="openai")
        with pytest.raises(AITransientError, match="Erro de rede"):
            await chain.generate("John", "male", "prev", "recs")

    @pytest.mark.asyncio
    @patch("src.ai.chains.report_generation.AsyncOpenAI")
    async def test_generate_error_mapping_transient(self, mock_openai):
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("503 Service Unavailable")
        )

        chain = ReportGenerationChain(provider="openai")
        with pytest.raises(AITransientError, match="Erro temporário"):
            await chain.generate("p", "g", "c", "r")

    @pytest.mark.asyncio
    @patch("src.ai.chains.report_generation.AsyncOpenAI")
    async def test_generate_error_mapping_fatal(self, mock_openai):
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("401 Unauthorized")
        )

        chain = ReportGenerationChain(provider="openai")
        with pytest.raises(AIFatalError, match="Erro fatal ocorrido"):
            await chain.generate("p", "g", "c", "r")

    @pytest.mark.asyncio
    @patch("src.ai.chains.report_generation.AsyncOpenAI")
    async def test_generate_error_mapping_unknown(self, mock_openai):
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("Unknown error")
        )

        chain = ReportGenerationChain(provider="openai")
        with pytest.raises(AIFatalError, match="Erro desconhecido"):
            await chain.generate("p", "g", "c", "r")
