from abc import ABC, abstractmethod
from functools import lru_cache

from app.core.config import get_settings

settings = get_settings()


class LLMNotConfiguredError(Exception):
    """Raised when no LLM API key is set. Callers turn this into a clear
    user-facing error rather than a stack trace or a fabricated answer."""


class LLMGenerationError(Exception):
    """Raised when a configured provider's API call itself fails (bad
    model name, rate limit, network issue, ...). Distinct from
    LLMNotConfiguredError so callers can give an equally honest message
    without conflating 'not set up' with 'set up but the call failed'."""


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str: ...


class GroqProvider(LLMProvider):
    """Groq exposes an OpenAI-compatible API with a free tier, so we reuse
    the `openai` client pointed at Groq's base URL instead of adding a
    provider-specific SDK. Swapping to OpenAI/Anthropic later means adding
    another small class here, not touching any call site."""

    def __init__(self, api_key: str, model: str) -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        self._model = model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        from openai import APIError

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
        except APIError as exc:
            raise LLMGenerationError(str(exc)) from exc
        return response.choices[0].message.content or ""


@lru_cache
def get_llm_provider() -> LLMProvider:
    if not settings.groq_api_key:
        raise LLMNotConfiguredError(
            "No LLM API key configured. Get a free key at https://console.groq.com "
            "and set GROQ_API_KEY in backend/.env."
        )
    return GroqProvider(settings.groq_api_key, settings.groq_model)
