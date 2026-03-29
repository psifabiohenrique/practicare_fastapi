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
            self.model = settings.LLM_MODEL  # User requested gpt-5-mini
        elif provider == "google":
            self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
            self.model = settings.LLM_MODEL
        else:
            raise ValueError(f"Provider {provider} not supported")

    async def generate(
        self,
        patient_first_name: str,
        gender: str,
        previous_report_context: str,
        records_context: str,
    ) -> AIResult:
        """
        Generates a structured report from records and context using OpenAI directly.
        """  # noqa: E501
        logger.info(
            f"Chamando LLM ({self.provider}) para geração de relatório. "
            f"Modelo: {self.model}"
        )
        try:
            system_prompt = REPORT_GENERATION_SYSTEM_PROMPT.format(
                patient_first_name=patient_first_name,
                gender=gender,
                previous_report_context=previous_report_context,
                records_context=records_context,
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
                    # temperature=0,
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
            # cobre DNS, timeout, falha de socket, etc.
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
