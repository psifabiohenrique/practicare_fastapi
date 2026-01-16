from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError

from src.ai.exceptions import AIFatalError, AITransientError
from src.ai.llm.factory import LLMFactory
from src.ai.llm.response_extractor import ResponseExtractor
from src.ai.prompts.record_prompts import RECORD_GENERATION_PROMPT


class RecordGenerationChain:
    def __init__(self, provider: str = "google"):
        self.llm = LLMFactory.get_llm(provider=provider)
        self.chain = RECORD_GENERATION_PROMPT | self.llm

    async def generate(self, transcription: str) -> str:
        """
        Generates a structured record from a transcription.
        """
        try:
            response = await self.chain.ainvoke({
                "transcription": transcription
            })
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
