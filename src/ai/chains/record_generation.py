from google import genai
from openai import AsyncOpenAI

from src.ai.exceptions import AIFatalError, AITransientError
from src.ai.prompts.record_prompts import RECORD_GENERATION_SYSTEM_PROMPT
from src.settings import settings


class RecordGenerationChain:
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
        self, transcription: str, gender: str, context: str
    ) -> str:
        """
        Generates a structured record from a transcription using OpenAI directly.
        """  # noqa: E501
        try:
            system_prompt = RECORD_GENERATION_SYSTEM_PROMPT.format(
                gender=gender, context=context
            )
            if self.provider == "openai":
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": f"Aqui está a transcrição do atendimento:\n\n{transcription}",  # noqa: E501
                        },
                    ],
                    # temperature=0,
                )
                return response.choices[0].message.content or ""
            elif self.provider == "google":
                response = self.client.models.generate_content(
                    model=self.model,
                    config=genai.types.GenerateContentConfig(
                        system_instruction=system_prompt, temperature=0.1
                    ),
                    contents=transcription,
                )
                return response.text

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
