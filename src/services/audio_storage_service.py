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
            # 'purpose' can be 'assistants' for long term but 'fine-tune' is not it.  # noqa: E501
            # Actually, Whisper doesn't use Files API for direct transcription,
            # but we will use it as a storage bridge since that's what was requested.  # noqa: E501
            # Note: Files API files are only accessible by certain APIs.
            # For Whisper, we will need to download it back.
            response = await client.files.create(
                file=(filename, content),
                purpose="assistants",  # Using assistants purpose as it allows retrieval  # noqa: E501
            )
            return response.id
        except Exception as e:
            logger.error(f"Failed to upload to OpenAI: {e}")
            raise

    @staticmethod
    async def get_file_content(file_id: str) -> bytes:
        """
        Re-downloads the file content from OpenAI.
        """
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        try:
            response = await client.files.content(file_id)
            return await response.read()
        except Exception as e:
            logger.error(f"Failed to download from OpenAI: {e}")
            raise

    @staticmethod
    async def delete_file(file_id: str):
        """
        Deletes the file from OpenAI.
        """
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        try:
            await client.files.delete(file_id)
        except Exception as e:
            logger.warning(f"Failed to delete file {file_id} from OpenAI: {e}")
            pass  # Non-critical
