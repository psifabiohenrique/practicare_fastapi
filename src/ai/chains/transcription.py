import logging
from openai import AsyncOpenAI
from src.ai.exceptions import AIFatalError, AITransientError
from src.settings import settings

logger = logging.getLogger(__name__)


class TranscriptionChain:
    def __init__(self, provider: str = "openai"):
        self.provider = provider
        if provider == "openai":
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            raise ValueError(
                f"Provider {provider} not supported for Whisper yet"
            )

    async def transcribe(
        self, audio_content: bytes, filename: str = "audio.webm"
    ) -> str:
        """
        Transcribes audio using OpenAI Whisper.
        """
        try:
            # Whisper requires a file-like object with a name attribute
            # We'll use a temporary file if needed, but the API accepts a tuple (filename, file_bytes)
            response = await self.client.audio.transcriptions.create(
                model="whisper-1",
                file=(filename, audio_content),
            )
            return response.text

        except Exception as e:
            err_msg = str(e).lower()
            logger.error(f"Error in transcription: {err_msg}")

            if any(
                sub in err_msg
                for sub in (
                    "429",
                    "rate limit",
                    "503",
                    "504",
                    "500",
                    "overloaded",
                )
            ):
                raise AITransientError(
                    f"Erro temporário na transcrição: {str(e)}"
                )

            if any(
                sub in err_msg
                for sub in (
                    "400",
                    "403",
                    "401",
                    "invalid_api_key",
                    "permission_denied",
                )
            ):
                raise AIFatalError(f"Erro fatal na transcrição: {str(e)}")

            raise AIFatalError(
                f"Erro desconhecido na transcrição: {str(e)}"
            ) from e
