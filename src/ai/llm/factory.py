from langchain_google_genai import ChatGoogleGenerativeAI

from src.settings import settings


class LLMFactory:
    @staticmethod
    def get_llm(provider: str = "google", **kwargs):
        """
        Returns an LLM instance based on the provider.
        Initially supports Google Gemini.
        """
        if provider == "google":
            model_name = kwargs.get(
                "model_name", settings.LLM_MODEL or "gemini-2.0-flash-exp"
            )
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=kwargs.get("temperature", 0),
                **kwargs,
            )

        # Add other providers (openai, anthropic) here if needed in the future
        raise ValueError(f"Unsupported provider: {provider}")
