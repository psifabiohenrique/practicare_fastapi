from langchain_core.output_parsers import JsonOutputParser
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError

from src.ai.exceptions import AIFatalError, AITransientError
from src.ai.llm.factory import LLMFactory
from src.ai.prompts.report_prompts import REPORT_GENERATION_PROMPT


class ReportGenerationChain:
    def __init__(self, provider: str = "google"):
        self.llm = LLMFactory.get_llm(provider=provider)
        self.parser = JsonOutputParser()
        self.chain = REPORT_GENERATION_PROMPT | self.llm | self.parser

    async def generate(
        self,
        patient_first_name: str,
        gender: str,
        previous_report_context: str,
        records_context: str,
    ) -> dict:
        """
        Generates a structured report from records and context.
        """
        try:
            response = await self.chain.ainvoke({
                "patient_first_name": patient_first_name,
                "gender": gender,
                "previous_report_context": previous_report_context,
                "records_context": records_context,
            })
            return response

        except ChatGoogleGenerativeAIError as e:
            if any(sub in str(e) for sub in ("429", "503", "504", "500")):
                raise AITransientError(f"Erro temporário: {str(e)}")
            if any(sub in str(e) for sub in ("400", "403", "401")):
                raise AIFatalError(f"Erro fatal ocorrido: {str(e)}")
        except Exception as e:
            raise AIFatalError(
                f"Erro desconhecido no processamento: {str(e)}"
            ) from e
