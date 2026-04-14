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
    CONTEXT_UPDATE_SYSTEM_PROMPT,
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


class ContextFieldDiff(BaseModel):
    """Structured diff for a single context field."""

    add: list[str] = []
    remove: list[str] = []


class ContextDraftJSON(BaseModel):
    """Full structured draft output from the AI for context update."""

    life_dynamics: ContextFieldDiff | None = None
    clinical_history: ContextFieldDiff | None = None
    psychological_patterns: ContextFieldDiff | None = None
    therapeutic_goals: ContextFieldDiff | None = None
    medication_notes: ContextFieldDiff | None = None


def extract_json(text: str) -> str:
    """
    Remove fences ```json ... ``` ou ``` ... ``` e retorna JSON puro.
    """
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_draft_response(raw: dict) -> dict:
    """
    Validates the raw AI output against ContextDraftJSON and converts it
    to a plain dict suitable for storing in the DB (each value is either
    None or {"add": [...], "remove": [...]}).
    """
    result = {}
    for field in CONTEXT_FIELDS:
        val = raw.get(field)
        if val is None:
            result[field] = None
            continue
        # If the AI returned the dict structure
        if isinstance(val, dict):
            result[field] = {
                "add": [
                    s
                    for s in val.get("add", [])
                    if isinstance(s, str) and s.strip()
                ],
                "remove": [
                    s
                    for s in val.get("remove", [])
                    if isinstance(s, str) and s.strip()
                ],
            }
        else:
            result[field] = None
    return result


class ContextUpdateChain:
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
        current_context: dict,
        record_content: str,
        gender: str,
    ) -> AIResult:
        """
        Generates a structured context update draft from the current
        context (list[str] per field) and a new record.
        Returns AIResult whose content is a dict with ContextFieldDiff
        values per field.
        """
        logger.info(
            f"Chamando LLM ({self.provider}) para atualização "
            f"de contexto clínico. Modelo: {self.model}"
        )

        # Render current context as bullet lists for the prompt
        context_text = ""
        for k, v in current_context.items():
            if v and isinstance(v, list):
                bullets = "\n".join(f"  - {b}" for b in v)
                context_text += f"{k}:\n{bullets}\n"
            else:
                context_text += f"{k}: Não definido\n"

        system_prompt = CONTEXT_UPDATE_SYSTEM_PROMPT.format(
            gender=gender,
            current_context=context_text,
            record_content=record_content,
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
                                "Atualize o contexto clínico com "
                                "base no prontuário fornecido."
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
                    "Resposta OpenAI (Contexto). Tokens: In %s, Out %s",
                    input_tokens,
                    output_tokens,
                )
                raw = json.loads(content)
                return AIResult(
                    content=parse_draft_response(raw),
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
                        "Atualize o contexto clínico com base "
                        "no prontuário fornecido, em JSON."
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
                    "Resposta Google (Contexto). Tokens: In %s, Out %s",
                    input_tokens,
                    output_tokens,
                )
                return AIResult(
                    content=parse_draft_response(raw),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )

        except (
            httpx.ConnectError,
            httpcore.ConnectError,
            socket.gaierror,
        ) as e:
            logger.error(
                "Erro de rede ao chamar o LLM (%s) para contexto: %s",
                self.provider,
                e,
            )
            raise AITransientError("Erro de rede ao chamar o LLM") from e

        except Exception as e:
            logger.error(
                "Erro inesperado ao atualizar contexto com %s: %s",
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
