from __future__ import annotations

import logging

from config.settings import Settings
from services.ai.base import AIProvider, AIResponse
from services.dialog_service import DialogService
from services.memory_service import MemoryService
from utils.file_blocks import extract_file_blocks, history_text_for_files, user_asks_for_file

logger = logging.getLogger(__name__)


class ChatService:
    """Оркестрация диалога ↔ память ↔ AI (без привязки к VK)."""

    def __init__(
        self,
        *,
        settings: Settings,
        dialogs: DialogService,
        memory: MemoryService,
        ai: AIProvider,
    ) -> None:
        self._settings = settings
        self._dialogs = dialogs
        self._memory = memory
        self._ai = ai

    @property
    def model_name(self) -> str:
        return self._ai.model_name

    async def reply(self, user_id: int, user_text: str) -> AIResponse:
        state = await self._dialogs.get_or_create_user(user_id)
        dialog = state.get_active_dialog()
        history = self._memory.build_context_messages(dialog)
        system_prompt = self._memory.system_prompt_for(dialog)

        prompt_user = user_text
        if user_asks_for_file(user_text):
            prompt_user = (
                f"{user_text}\n\n"
                "[Системная подсказка: пользователь явно просит файл. "
                "Обязательно приложи содержимое в блоке <<<VK_FILE name=\"...\">>> … <<<END_VK_FILE>>>]"
            )

        logger.info(
            "AI-запрос user=%s dialog=%s mode=%s history=%s file_intent=%s",
            user_id,
            dialog.id,
            dialog.mode,
            len(history),
            user_asks_for_file(user_text),
        )

        response = await self._ai.generate(
            system_prompt=system_prompt,
            history=history,
            user_message=prompt_user,
        )

        chat_text, files = extract_file_blocks(response.text)
        response.text = chat_text
        response.files = files

        await self._memory.append_exchange(
            dialog,
            user_text=user_text,
            assistant_text=history_text_for_files(chat_text, files),
        )
        await self._dialogs.save(state)
        return response

    async def clear_active_history(self, user_id: int) -> None:
        state = await self._dialogs.get_or_create_user(user_id)
        dialog = state.get_active_dialog()
        await self._memory.clear_history(dialog)
        await self._dialogs.save(state)
