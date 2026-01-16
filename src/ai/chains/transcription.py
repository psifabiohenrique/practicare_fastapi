import base64

from langchain_core.messages import HumanMessage
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError

from src.ai.exceptions import AIFatalError, AITransientError
from src.ai.llm.factory import LLMFactory
from src.ai.llm.response_extractor import ResponseExtractor


class TranscriptionChain:
    def __init__(self, provider: str = "google"):
        # We need a multimodal model for audio transcription
        self.llm = LLMFactory.get_llm(provider=provider)

    async def transcribe(
        self, audio_bytes: bytes, mime_type: str = "audio/webm"
    ) -> str:
        """
        Transcribes audio bytes using Gemini's multimodal capabilities.
        """
        # Convert audio bytes to base64 for LangChain/Gemini input
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        message = HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": (
                        "Transcreva o áudio a seguir da forma mais fiel "
                        "possível, focando no conteúdo de saúde."
                    ),
                },
                {
                    "type": "media",
                    "mime_type": mime_type,
                    "data": audio_base64,
                },
            ]
        )

        try:
            response = await self.llm.ainvoke([message])
            return ResponseExtractor.extract_text(response)
        except ChatGoogleGenerativeAIError as e:
            if any(sub in str(e) for sub in ("429", "503", "504", "500")):
                raise AITransientError(f"Erro temporário: {str(e)}")
        except ChatGoogleGenerativeAIError as e:
            if any(sub in str(e) for sub in ("400", "403", "401")):
                raise AIFatalError(f"Erro fatal ocorrido: {str(e)}")
        except Exception as e:
            # Erros genéricos (rede, LangChain, etc.)
            raise AIFatalError(
                f"Erro desconhecido no processamento: {str(e)}"
            ) from e
