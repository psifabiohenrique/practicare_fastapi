import logging

from google import genai

from src.ai.ai_result import AIResult
from src.ai.exceptions import AIFatalError, AITransientError
from src.settings import settings

logger = logging.getLogger(__name__)


class TranscriptionChain:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    async def upload_audio(self, file_path: str) -> str:
        logger.info(f"Upload de áudio para Google GenAI: {file_path}")
        try:
            response = await self.client.aio.files.upload(file=file_path)
            logger.info(
                f"Upload para Google GenAI concluído. File name: {response}"
            )
            return response
        except Exception as e:
            logger.error(
                f"Erro no upload para Google GenAI: {e}", exc_info=True
            )
            raise AIFatalError(
                f"Erro ao enviar áudio para transcrição: {str(e)}"
            ) from e

    async def transcribe(self, file_name: str) -> AIResult:
        logger.info(f"Iniciando transcrição para o arquivo: {file_name}")
        try:
            file = self.client.files.get(name=file_name)
            if file.state != genai.types.FileState.ACTIVE:
                logger.warning(
                    f"Arquivo {file_name} não está pronto "
                    f"(State: {file.state})"
                )
                raise AITransientError(
                    "O arquivo de áudio ainda não está pronto para "
                    "transcrição."  # noqa: E501
                )

            response = self.client.models.generate_content(
                model=settings.TRANSCRIPTION_MODEL,
                contents=[
                    "transcreva este trecho de atendimento clínico de forma "
                    "precisa e detalhada.",  # noqa: E501
                    file,
                ],
            )

            input_tokens = 0
            output_tokens = 0
            if response.usage_metadata:
                input_tokens = response.usage_metadata.prompt_token_count or 0
                output_tokens = (
                    response.usage_metadata.candidates_token_count or 0
                )

            logger.info(
                f"Transcrição concluída para {file_name}. Tokens: "
                f"In {input_tokens}, Out {output_tokens}"
            )
            return AIResult(
                content=response.text,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

        except AITransientError as e:
            raise e

        except Exception as e:
            err_msg = str(e).lower()
            logger.error(
                f"Erro na transcrição de {file_name}: {err_msg}",
                exc_info=True,
            )

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
