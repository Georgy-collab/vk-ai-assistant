from __future__ import annotations

import asyncio
import logging

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from config.prompts import SUMMARY_SYSTEM_PROMPT
from models.entities import ChatMessage
from services.ai.base import AIProvider, AIResponse

logger = logging.getLogger(__name__)

FALLBACK_TEXT = (
    "Сейчас не удалось получить ответ от модели. "
    "Попробуйте ещё раз через минуту. Если ошибка повторяется — проверьте баланс ProxyAPI."
)
MODEL_UNSUPPORTED_FALLBACK = (
    "Модель «{model}» не поддерживается ProxyAPI. "
    "Укажите другое значение GEMINI_MODEL в .env и перезапустите бота."
)


def _is_model_not_supported(exc: BaseException) -> bool:
    text = str(exc).lower()
    if "model not supported" in text:
        return True
    details = getattr(exc, "details", None)
    if isinstance(details, dict) and "model not supported" in str(details).lower():
        return True
    message = getattr(exc, "message", None)
    if message and "model not supported" in str(message).lower():
        return True
    return False


def _log_ai_failure(context: str, model: str, exc: BaseException) -> None:
    if _is_model_not_supported(exc):
        logger.error(
            "Модель не поддерживается: «%s». "
            "ProxyAPI вернул ошибку Model not supported. "
            "Смените GEMINI_MODEL в .env на актуальную из каталога ProxyAPI. Контекст: %s. Детали: %s",
            model,
            context,
            exc,
        )
        return
    if isinstance(exc, genai_errors.APIError):
        logger.error(
            "Ошибка Gemini/ProxyAPI (%s): код=%s, модель=%s, детали=%s",
            context,
            getattr(exc, "code", "?"),
            model,
            exc,
        )
        return
    logger.exception("Ошибка Gemini/ProxyAPI при %s (модель=%s)", context, model)


class GeminiAIService(AIProvider):
    """Gemini через ProxyAPI с официальным Google GenAI SDK."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        api_version: str,
        model: str,
        timeout_seconds: float = 60.0,
    ) -> None:
        self._model = model
        self._timeout = timeout_seconds
        self._client = genai.Client(
            api_key=api_key,
            http_options={
                "base_url": base_url.rstrip("/"),
                "api_version": api_version,
            },
        )

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(
        self,
        *,
        system_prompt: str,
        history: list[ChatMessage],
        user_message: str,
    ) -> AIResponse:
        contents = self._history_to_contents(history)
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part(text=user_message)],
            )
        )
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.7,
        )

        try:
            response = await asyncio.wait_for(
                self._generate_content(contents=contents, config=config),
                timeout=self._timeout,
            )
            text = (response.text or "").strip()
            if not text:
                logger.warning("Пустой ответ модели %s", self._model)
                return AIResponse(text=FALLBACK_TEXT, model=self._model, finish_reason="empty")
            return AIResponse(
                text=text,
                model=self._model,
                finish_reason=getattr(response, "finish_reason", None),
            )
        except Exception as exc:
            _log_ai_failure("generate", self._model, exc)
            if _is_model_not_supported(exc):
                return AIResponse(
                    text=MODEL_UNSUPPORTED_FALLBACK.format(model=self._model),
                    model=self._model,
                    finish_reason="model_not_supported",
                )
            return AIResponse(text=FALLBACK_TEXT, model=self._model, finish_reason="error")

    async def summarize(self, *, messages: list[ChatMessage]) -> str:
        if not messages:
            return ""

        transcript = "\n".join(f"{msg.role}: {msg.content}" for msg in messages)
        contents = [
            types.Content(
                role="user",
                parts=[types.Part(text=f"Переписка для резюме:\n\n{transcript}")],
            )
        ]
        config = types.GenerateContentConfig(
            system_instruction=SUMMARY_SYSTEM_PROMPT,
            temperature=0.2,
        )
        try:
            response = await asyncio.wait_for(
                self._generate_content(contents=contents, config=config),
                timeout=self._timeout,
            )
            text = (response.text or "").strip()
            return text or "Краткое резюме недоступно."
        except Exception as exc:
            _log_ai_failure("summarize", self._model, exc)
            # Локальный fallback без API
            joined = " ".join(msg.content for msg in messages)
            return joined[:1000]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    async def _generate_content(
        self,
        *,
        contents: list[types.Content],
        config: types.GenerateContentConfig,
    ):
        return await self._client.aio.models.generate_content(
            model=self._model,
            contents=contents,
            config=config,
        )

    @staticmethod
    def _history_to_contents(history: list[ChatMessage]) -> list[types.Content]:
        contents: list[types.Content] = []
        for msg in history:
            if msg.role == "system":
                # System prompt передаётся отдельно; summary в истории как user-контекст
                role = "user"
                text = f"[Контекст/резюме]\n{msg.content}"
            elif msg.role == "assistant":
                role = "model"
                text = msg.content
            else:
                role = "user"
                text = msg.content
            contents.append(
                types.Content(role=role, parts=[types.Part(text=text)])
            )
        return contents
