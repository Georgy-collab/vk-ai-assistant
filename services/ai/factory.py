from config.settings import Settings
from services.ai.base import AIProvider
from services.ai.gemini_service import GeminiAIService


def create_ai_service(settings: Settings) -> AIProvider:
    """Фабрика провайдеров: сейчас Gemini, позже легко добавить OpenAI и др."""
    return GeminiAIService(
        api_key=settings.api_key,
        base_url=settings.proxy_gemini_base_url,
        api_version=settings.proxy_gemini_api_version,
        model=settings.gemini_model,
        timeout_seconds=settings.ai_timeout_seconds,
    )
