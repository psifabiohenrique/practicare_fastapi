import logging

from google import genai

from src.ai.exceptions import AIFatalError, AITransientError
from src.settings import settings

logger = logging.getLogger(__name__)


class TranscriptionChain:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    async def upload_audio(self, file_path: str) -> str:
        try:
            response = await self.client.aio.files.upload(file=file_path)
            return response
        except Exception as e:
            logger.error(f"Error uploading audio to Google GenAI: {str(e)}")
            raise AIFatalError(
                f"Erro ao enviar áudio para transcrição: {str(e)}"
            ) from e

    async def transcribe(self, file_name: str) -> str:
        try:
            file = self.client.files.get(name=file_name)
            if file.state != genai.types.FileState.ACTIVE:
                raise AITransientError(
                    "O arquivo de áudio ainda não está pronto para transcrição."  # noqa: E501
                )

            response = self.client.models.generate_content(
                model=settings.TRANSCRIPTION_MODEL,
                contents=[
                    "transcreva este trecho de atendimento clínico de forma precisa e detalhada.",  # noqa: E501
                    file,
                ],
            )
            return response.text

        except AITransientError as e:
            raise e

        except Exception as e:
            err_msg = str(e).lower()
            logger.error(f"Error in transcription: {err_msg}")

            if any(
                sub in err_msg
                for sub in (
                    "400",
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
