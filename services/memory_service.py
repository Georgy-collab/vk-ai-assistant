from __future__ import annotations

import logging

from config.prompts import get_system_prompt
from config.settings import Settings
from models.entities import ChatMessage, Dialog
from services.ai.base import AIProvider

logger = logging.getLogger(__name__)


class MemoryService:
    """Краткосрочная память диалога + авто-резюме при превышении лимита."""

    def __init__(self, settings: Settings, ai: AIProvider) -> None:
        self._settings = settings
        self._ai = ai

    def build_context_messages(self, dialog: Dialog) -> list[ChatMessage]:
        """Берёт до N последних сообщений активного диалога."""
        limit = self._settings.max_history_messages
        return list(dialog.messages[-limit:])

    def system_prompt_for(self, dialog: Dialog) -> str:
        return get_system_prompt(dialog.mode)

    async def append_exchange(
        self,
        dialog: Dialog,
        *,
        user_text: str,
        assistant_text: str,
    ) -> None:
        dialog.messages.append(ChatMessage(role="user", content=user_text))
        dialog.messages.append(ChatMessage(role="assistant", content=assistant_text))
        dialog.touch()
        await self._compact_if_needed(dialog)

    async def clear_history(self, dialog: Dialog) -> None:
        dialog.messages.clear()
        dialog.touch()

    async def _compact_if_needed(self, dialog: Dialog) -> None:
        limit = self._settings.max_history_messages
        if len(dialog.messages) <= limit:
            return

        batch = self._settings.summary_batch_size
        overflow = len(dialog.messages) - limit
        # Суммируем первые сообщения так, чтобы после вставки резюме уложиться в лимит
        to_summarize_count = max(batch, overflow + 1)
        to_summarize_count = min(to_summarize_count, len(dialog.messages) - 1)
        old_part = dialog.messages[:to_summarize_count]
        rest = dialog.messages[to_summarize_count:]

        logger.info(
            "Сжатие истории диалога %s: %s → резюме + %s",
            dialog.id,
            to_summarize_count,
            len(rest),
        )
        summary_text = await self._ai.summarize(messages=old_part)
        summary = ChatMessage(
            role="system",
            content=summary_text,
            is_summary=True,
        )
        dialog.messages = [summary, *rest]

        # На всякий случай, если всё ещё больше лимита
        if len(dialog.messages) > limit:
            dialog.messages = dialog.messages[-limit:]
