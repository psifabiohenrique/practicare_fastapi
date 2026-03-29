import logging
import uuid

from openai import AsyncOpenAI

from src.settings import settings

logger = logging.getLogger(__name__)


class AudioStorageService:
    @staticmethod
    async def save_upload(
        upload_file,
    ) -> str:
        """
        Uploads the file to OpenAI Files API and returns the file_id.
        """
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        # We need to read the file content
        content = await upload_file.read()
        suffix = (
            upload_file.filename.split(".")[-1]
            if "." in upload_file.filename
            else "webm"
        )
        filename = f"{uuid.uuid4()}.{suffix}"

        try:
            # Upload to OpenAI
            logger.info(f"Fazendo upload de arquivo para OpenAI: {filename}")
            response = await client.files.create(
                file=(filename, content),
                purpose="assistants",  # Using assistants purpose as it allows retrieval  # noqa: E501
            )
            logger.info(
                "Upload concluído com sucesso. File ID: %s", response.id
            )
            return response.id
        except Exception as e:
            logger.error(
                "Falha ao fazer upload para OpenAI: %s", e, exc_info=True
            )
            raise

    @staticmethod
    async def get_file_content(file_id: str) -> bytes:
        """
        Re-downloads the file content from OpenAI.
        """
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        try:
            logger.info(f"Baixando conteúdo do arquivo OpenAI: {file_id}")
            response = await client.files.content(file_id)
            return await response.read()
        except Exception as e:
            logger.error(
                "Falha ao baixar arquivo do OpenAI: %s", e, exc_info=True
            )
            raise

    @staticmethod
    async def delete_file(file_id: str):
        """
        Deletes the file from OpenAI.
        """
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        try:
            logger.info(f"Excluindo arquivo do OpenAI: {file_id}")
            await client.files.delete(file_id)
        except Exception as e:
            logger.warning(
                "Falha ao excluir arquivo %s do OpenAI: %s", file_id, e
            )
            pass  # Non-critical
