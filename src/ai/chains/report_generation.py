import json
import logging
import re
import socket

import httpcore
import httpx
from google import genai
from openai import AsyncOpenAI
from pydantic import BaseModel

from src.ai.ai_result import AIResult
from src.ai.exceptions import AIFatalError, AITransientError
from src.ai.prompts.report_prompts import REPORT_GENERATION_SYSTEM_PROMPT
from src.settings import settings

logger = logging.getLogger(__name__)


class ReportJSON(BaseModel):
    demand_description: str
    procedures: str
    analysis: str
    conclusion: str


def extract_json(text: str) -> str:
    """
    Remove fences ```json ... ``` ou ``` ... ``` e retorna JSON puro.
    """
    text = text.strip()

    # Caso venha em markdown
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    return text.strip()


class ReportGenerationChain:
    def __init__(self, provider: str = settings.LLM_PROVIDER):
        self.provider = provider
        if provider == "openai":
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = settings.LLM_MODEL
        elif provider == "google":
            self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
            self.model = settings.LLM_MODEL
        else:
            raise ValueError(f"Provider {provider} not supported")

    async def generate(
        self,
        patient_first_name: str,
        gender: str,
        records_context: str,
        treatment_context: str | None = None,
        custom_system_prompt: str | None = None,
    ) -> AIResult:
        """
        Generates a structured report from records and context using an LLM.
        - treatment_context: accumulated clinical context for the treatment.
        - custom_system_prompt: extra instruction for focused reports,
          appended to the default system prompt.
        """  # noqa: E501
        logger.info(
            f"Chamando LLM ({self.provider}) para geração de relatório. "
            f"Modelo: {self.model}"
        )
        try:
            context_text = (
                treatment_context
                if treatment_context
                else "Sem contexto clínico disponível."
            )

            system_prompt = REPORT_GENERATION_SYSTEM_PROMPT.format(
                patient_first_name=patient_first_name,
                gender=gender,
                treatment_context=context_text,
                records_context=records_context,
            )

            # Append custom instruction for focused reports
            if custom_system_prompt:
                system_prompt += (
                    f"\n\n[Instrução Específica do Usuário]\n"
                    f"{custom_system_prompt}\n"
                    f"Atenção: mesmo com a instrução acima, "
                    f"mantenha o formato de saída JSON obrigatório."
                )

            if self.provider == "openai":
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": f"Gere o relatório para o paciente {patient_first_name}.",  # noqa: E501
                        },
                    ],
                    response_format={"type": "json_object"},
                )
                input_tokens = 0
                output_tokens = 0
                if response.usage:
                    input_tokens = response.usage.prompt_tokens or 0
                    output_tokens = response.usage.completion_tokens or 0

                content = response.choices[0].message.content or "{}"
                logger.info(
                    "Resposta recebida da OpenAI (Relatório). "
                    f"Tokens: In {input_tokens}, Out {output_tokens}"
                )
                return AIResult(
                    content=json.loads(content),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
            elif self.provider == "google":
                response = self.client.models.generate_content(
                    model=self.model,
                    config=genai.types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.1,
                    ),
                    contents=[
                        f"Gere o relatório para o paciente {patient_first_name} em JSON estruturado."  # noqa: E501
                    ],
                )
                input_tokens = 0
                output_tokens = 0
                if response.usage_metadata:
                    input_tokens = (
                        response.usage_metadata.prompt_token_count or 0
                    )
                    output_tokens = (
                        response.usage_metadata.candidates_token_count or 0
                    )
                report = ReportJSON.model_validate_json(
                    extract_json(response.text)
                )
                logger.info(
                    "Resposta recebida do Google (Relatório). "
                    f"Tokens: In {input_tokens}, Out {output_tokens}"
                )
                return AIResult(
                    content=report,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )

        except (
            httpx.ConnectError,
            httpcore.ConnectError,
            socket.gaierror,
        ) as e:
            logger.error(
                f"Erro de rede ao chamar o LLM ({self.provider}) "
                f"para relatório: {e}"
            )
            raise AITransientError("Erro de rede ao chamar o Gemini") from e

        except Exception as e:
            logger.error(
                f"Erro inesperado ao gerar relatório com {self.provider}: {e}",
                exc_info=True,
            )
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
