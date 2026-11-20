from __future__ import annotations

import asyncio
import logging

from vkbottle.bot import Bot, Message
from vkbottle.tools import DocMessagesUploader

from bot.container import AppContainer
from keyboards.menus import (
    dialogs_keyboard,
    help_text,
    main_menu_keyboard,
    modes_keyboard,
    settings_keyboard,
    welcome_text,
)
from models.entities import GeneratedFile
from services.document_service import DocumentService
from utils.text import prepare_vk_message_parts, sanitize_user_text

logger = logging.getLogger(__name__)

# В VK статус «печатает» живёт ~10 секунд и сбрасывается любой отправкой сообщения.
TYPING_REFRESH_SECONDS = 4.0


async def _send_typing(bot: Bot, *, peer_id: int, group_id: int | None) -> None:
    kwargs: dict = {"peer_id": peer_id, "type": "typing"}
    if group_id:
        kwargs["group_id"] = group_id
    await bot.api.messages.set_activity(**kwargs)


async def _keep_typing(
    bot: Bot,
    *,
    peer_id: int,
    group_id: int | None,
    stop_event: asyncio.Event,
) -> None:
    """Пока идёт генерация, периодически шлёт «печатает…» в диалог."""
    while not stop_event.is_set():
        try:
            await _send_typing(bot, peer_id=peer_id, group_id=group_id)
            logger.debug("typing отправлен peer_id=%s group_id=%s", peer_id, group_id)
        except Exception:
            logger.warning(
                "Не удалось отправить статус «печатает» (peer_id=%s, group_id=%s)",
                peer_id,
                group_id,
                exc_info=True,
            )
            return
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=TYPING_REFRESH_SECONDS)
        except asyncio.TimeoutError:
            continue

MENU_COMMANDS = {
    "начать",
    "start",
    "/start",
    "меню",
    "/menu",
}


async def _send_generated_files(bot: Bot, message: Message, files: list[GeneratedFile]) -> None:
    prepared = DocumentService().prepare(files)
    if not prepared:
        await message.answer(
            "Не удалось подготовить файл. Попробуйте другое имя или расширение "
            "(txt, md, py, json, csv…).",
            keyboard=main_menu_keyboard(),
        )
        return

    uploader = DocMessagesUploader(bot.api)
    for filename, data in prepared:
        try:
            attachment = await uploader.upload(
                data,
                peer_id=message.peer_id,
                title=filename,
            )
            await message.answer(
                f"📎 Файл «{filename}»",
                attachment=attachment,
                keyboard=main_menu_keyboard(),
            )
        except Exception:
            logger.exception("Не удалось загрузить файл %s в VK", filename)
            await message.answer(
                f"Не удалось отправить файл «{filename}». Проверьте права сообщества на документы.",
                keyboard=main_menu_keyboard(),
            )


def register_message_handlers(bot: Bot, container: AppContainer) -> None:
    settings = container.settings
    dialogs = container.dialogs
    chat = container.chat

    @bot.on.message(text=["Начать", "начать", "Start", "start", "/start", "Меню", "меню", "/menu"])
    async def open_menu(message: Message) -> None:
        await dialogs.get_or_create_user(message.from_id)
        await message.answer(welcome_text(), keyboard=main_menu_keyboard())

    @bot.on.message(payload={"cmd": "new_dialog"})
    async def new_dialog(message: Message) -> None:
        state = await dialogs.create_dialog(message.from_id)
        dialog = state.get_active_dialog()
        await message.answer(
            f"Создан диалог «{dialog.title}». Можете писать сообщение.",
            keyboard=main_menu_keyboard(),
        )

    @bot.on.message(payload={"cmd": "list_dialogs"})
    async def list_dialogs(message: Message) -> None:
        state = await dialogs.get_or_create_user(message.from_id)
        await message.answer(
            dialogs.format_dialogs_list(state),
            keyboard=dialogs_keyboard(state),
        )

    @bot.on.message(payload={"cmd": "change_mode"})
    async def change_mode(message: Message) -> None:
        await message.answer(
            "Выберите режим общения для текущего диалога:",
            keyboard=modes_keyboard(),
        )

    @bot.on.message(payload={"cmd": "settings"})
    async def settings_handler(message: Message) -> None:
        state = await dialogs.get_or_create_user(message.from_id)
        text = dialogs.format_status(state, chat.model_name)
        await message.answer(text, keyboard=settings_keyboard())

    @bot.on.message(payload={"cmd": "help"})
    async def help_handler(message: Message) -> None:
        await message.answer(help_text(), keyboard=main_menu_keyboard())

    @bot.on.message()
    async def chat_handler(message: Message) -> None:
        user_id = message.from_id
        raw = message.text or ""
        normalized = raw.strip().lower()

        if normalized in MENU_COMMANDS:
            await open_menu(message)
            return

        state = await dialogs.get_or_create_user(user_id)

        if state.settings.pending_action == "rename_dialog" and state.settings.pending_dialog_id:
            title = sanitize_user_text(raw, 64)
            if not title:
                await message.answer("Название не может быть пустым. Пришлите текст.")
                return
            updated = await dialogs.rename_dialog(
                user_id,
                state.settings.pending_dialog_id,
                title,
            )
            if updated is None:
                await message.answer("Диалог не найден.", keyboard=main_menu_keyboard())
                return
            await message.answer(
                f"Диалог переименован в «{title}».",
                keyboard=dialogs_keyboard(updated),
            )
            return

        text = sanitize_user_text(raw, settings.max_user_message_length)
        if text is None:
            await message.answer(
                "Пустое сообщение. Напишите вопрос текстом или откройте меню.",
                keyboard=main_menu_keyboard(),
            )
            return

        # Сначала статусное сообщение (оно сбрасывает typing), потом крутим «печатает…».
        status_id = await message.answer("⏳ Бот думает...")
        group_id = message.group_id or getattr(bot.state, "group_id", None)
        stop_typing = asyncio.Event()
        typing_task = asyncio.create_task(
            _keep_typing(
                bot,
                peer_id=message.peer_id,
                group_id=group_id,
                stop_event=stop_typing,
            ),
            name=f"typing-{message.peer_id}",
        )
        try:
            response = await chat.reply(user_id, text)
        finally:
            stop_typing.set()
            try:
                await typing_task
            except Exception:
                logger.warning("Ошибка задачи typing", exc_info=True)

        try:
            await bot.api.messages.delete(
                peer_id=message.peer_id,
                message_ids=status_id,
                delete_for_all=1,
            )
        except Exception:
            logger.debug("Не удалось удалить статусное сообщение", exc_info=True)

        for part in prepare_vk_message_parts(response.text, settings.max_vk_message_length):
            await message.answer(part, keyboard=main_menu_keyboard())

        if response.files:
            await _send_generated_files(bot, message, response.files)
