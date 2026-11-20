from __future__ import annotations

import logging

from vkbottle import GroupEventType
from vkbottle.bot import Bot, MessageEvent

from bot.container import AppContainer
from config.prompts import ROLE_TITLES, RoleMode, get_role_title
from keyboards.menus import (
    dialogs_keyboard,
    main_menu_keyboard,
    modes_keyboard,
    settings_keyboard,
)

logger = logging.getLogger(__name__)


def register_callback_handlers(bot: Bot, container: AppContainer) -> None:
    dialogs = container.dialogs
    chat = container.chat

    @bot.on.raw_event(GroupEventType.MESSAGE_EVENT, dataclass=MessageEvent)
    async def on_message_event(event: MessageEvent) -> None:
        payload = event.get_payload_json() or {}
        cmd = payload.get("cmd")
        user_id = event.user_id

        try:
            await event.send_empty_answer()
        except Exception:
            logger.debug("send_empty_answer failed", exc_info=True)

        async def show(text: str, keyboard: str | None = None) -> None:
            await event.send_message(message=text, keyboard=keyboard)

        if cmd == "menu":
            await show("Главное меню:", main_menu_keyboard())
            return

        if cmd == "change_mode":
            await show("Выберите режим общения:", modes_keyboard())
            return

        if cmd == "settings":
            state = await dialogs.get_or_create_user(user_id)
            await show(dialogs.format_status(state, chat.model_name), settings_keyboard())
            return

        if cmd == "model_info":
            state = await dialogs.get_or_create_user(user_id)
            dialog = state.get_active_dialog()
            await show(
                f"Текущая модель: {chat.model_name}\n"
                f"Режим диалога: {ROLE_TITLES[dialog.mode]}\n"
                f"Провайдер: ProxyAPI (Google GenAI SDK)",
                settings_keyboard(),
            )
            return

        if cmd == "clear_history":
            await chat.clear_active_history(user_id)
            await show("История активного диалога очищена.", settings_keyboard())
            return

        if cmd == "set_mode":
            mode_raw = payload.get("mode")
            try:
                mode = RoleMode(mode_raw)
            except ValueError:
                await show("Неизвестный режим.", modes_keyboard())
                return
            state = await dialogs.set_mode(user_id, mode, for_active=True)
            dialog = state.get_active_dialog()
            await show(
                f"Режим «{get_role_title(mode)}» включён для диалога «{dialog.title}».",
                main_menu_keyboard(),
            )
            return

        if cmd == "switch_dialog":
            dialog_id = payload.get("id")
            state = await dialogs.switch_dialog(user_id, dialog_id)
            if state is None:
                await show("Диалог не найден.", main_menu_keyboard())
                return
            dialog = state.get_active_dialog()
            await show(
                f"Активный диалог: «{dialog.title}»\n"
                f"Режим: {get_role_title(dialog.mode)}\n"
                f"Сообщений: {len(dialog.messages)}",
                dialogs_keyboard(state),
            )
            return

        if cmd == "rename_dialog":
            dialog_id = payload.get("id")
            await dialogs.set_pending(user_id, "rename_dialog", dialog_id)
            await show(
                "Пришлите новое название диалога следующим сообщением.",
                main_menu_keyboard(),
            )
            return

        if cmd == "delete_dialog":
            dialog_id = payload.get("id")
            state = await dialogs.delete_dialog(user_id, dialog_id)
            if state is None:
                await show(
                    "Нельзя удалить последний диалог. Создайте новый и попробуйте снова.",
                    main_menu_keyboard(),
                )
                return
            await show("Диалог удалён.", dialogs_keyboard(state))
            return

        logger.warning("Неизвестный callback: %s", payload)
