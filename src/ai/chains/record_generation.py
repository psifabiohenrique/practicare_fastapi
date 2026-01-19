from src.ai.exceptions import AIFatalError, AITransientError
from src.ai.llm.factory import LLMFactory
from src.ai.llm.response_extractor import ResponseExtractor
from src.ai.prompts.record_prompts import RECORD_GENERATION_PROMPT


class RecordGenerationChain:
    def __init__(self, provider: str = "openai"):
        self.llm = LLMFactory.get_llm(provider=provider)
        self.chain = RECORD_GENERATION_PROMPT | self.llm

    async def generate(
        self, transcription: str, gender: str, context: str
    ) -> str:  # pyright: ignore[reportReturnType]
        """
        Generates a structured record from a transcription.
        """
        try:
            response = await self.chain.ainvoke({
                "transcription": transcription,
                "gender": gender,
                "context": context,
            })
            return ResponseExtractor.extract_text(response)

        except Exception as e:
            err_msg = str(e).lower()
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
                raise AITransientError(f"Erro temporário: {str(e)}")

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
                raise AIFatalError(f"Erro fatal ocorrido: {str(e)}")

            # Generic error
            raise AIFatalError(
                f"Erro desconhecido no processamento: {str(e)}"
            ) from e
