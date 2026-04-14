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
from src.ai.prompts.context_update_prompts import (
    CONTEXT_GENERATION_SYSTEM_PROMPT,
)
from src.settings import settings

logger = logging.getLogger(__name__)

CONTEXT_FIELDS = [
    "life_dynamics",
    "clinical_history",
    "psychological_patterns",
    "therapeutic_goals",
    "medication_notes",
]


class ContextGenerationJSON(BaseModel):
    """Full context output from the AI for generation — list[str] per field."""

    life_dynamics: list[str] | None = None
    clinical_history: list[str] | None = None
    psychological_patterns: list[str] | None = None
    therapeutic_goals: list[str] | None = None
    medication_notes: list[str] | None = None


def extract_json(text: str) -> str:
    """
    Remove fences ```json ... ``` ou ``` ... ``` e retorna JSON puro.
    """
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_generation_response(raw: dict) -> dict:
    """
    Validates and normalises the AI output for context generation.
    Each field must be a list[str] or None.
    If the AI returns a plain string (old format fallback), wrap it.
    """
    result = {}
    for field in CONTEXT_FIELDS:
        val = raw.get(field)
        if not val:
            result[field] = None
        elif isinstance(val, list):
            cleaned = [s for s in val if isinstance(s, str) and s.strip()]
            result[field] = cleaned if cleaned else None
        elif isinstance(val, str) and val.strip():
            # Fallback: if the AI returned a string, split on newlines
            lines = [
                ln.lstrip("- ").strip()
                for ln in val.splitlines()
                if ln.strip()
            ]
            result[field] = lines if lines else None
        else:
            result[field] = None
    return result


class ContextGenerationChain:
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
        base_material: str,
        gender: str,
    ) -> AIResult:
        """
        Generates a completely new clinical context as lists of bullet
        strings per field (list[str] | None).
        """
        logger.info(
            f"Chamando LLM ({self.provider}) para GERAÇÃO "
            f"de contexto clínico. Modelo: {self.model}"
        )

        system_prompt = CONTEXT_GENERATION_SYSTEM_PROMPT.format(
            gender=gender,
            base_material=base_material,
        )

        try:
            if self.provider == "openai":
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt,
                        },
                        {
                            "role": "user",
                            "content": (
                                "Gere o contexto clínico com "
                                "base no material fornecido."
                            ),
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
                    "Resposta OpenAI (Geração). Tokens: In %s, Out %s",
                    input_tokens,
                    output_tokens,
                )
                raw = json.loads(content)
                return AIResult(
                    content=parse_generation_response(raw),
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
                        "Gere o contexto clínico com base "
                        "no material fornecido, em JSON."
                    ],
                )
                input_tokens = 0
                output_tokens = 0
                if response.usage_metadata:
                    input_tokens = (
                        response.usage_metadata.prompt_token_count or 0
                    )
                    output_tokens = (
                        response.usage_metadata.candidates_token_count  # noqa: E501
                        or 0
                    )
                raw = json.loads(extract_json(response.text))
                logger.info(
                    "Resposta Google (Geração). Tokens: In %s, Out %s",
                    input_tokens,
                    output_tokens,
                )
                return AIResult(
                    content=parse_generation_response(raw),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )

        except (
            httpx.ConnectError,
            httpcore.ConnectError,
            socket.gaierror,
        ) as e:
            logger.error(
                "Erro de rede ao chamar o LLM (%s) para geração: %s",
                self.provider,
                e,
            )
            raise AITransientError("Erro de rede ao chamar o LLM") from e

        except Exception as e:
            logger.error(
                "Erro inesperado ao gerar contexto com %s: %s",
                self.provider,
                e,
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
