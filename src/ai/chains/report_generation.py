import json

from openai import AsyncOpenAI

from src.ai.exceptions import AIFatalError, AITransientError
from src.ai.prompts.report_prompts import REPORT_GENERATION_SYSTEM_PROMPT
from src.settings import settings


class ReportGenerationChain:
    def __init__(self, provider: str = "openai"):
        self.provider = provider
        if provider == "openai":
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = "gpt-5-mini"  # User requested gpt-5-mini
        else:
            raise ValueError(f"Provider {provider} not supported")

    async def generate(
        self,
        patient_first_name: str,
        gender: str,
        previous_report_context: str,
        records_context: str,
    ) -> dict:
        """
        Generates a structured report from records and context using OpenAI directly.
        """  # noqa: E501
        try:
            system_prompt = REPORT_GENERATION_SYSTEM_PROMPT.format(
                patient_first_name=patient_first_name,
                gender=gender,
                previous_report_context=previous_report_context,
                records_context=records_context,
            )

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Gere o relatório para o paciente {patient_first_name}.",  # noqa: E501
                    },
                ],
                temperature=0,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            return json.loads(content)

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
            raise AIFatalError(
                f"Erro desconhecido no processamento: {str(e)}"
            ) from e
