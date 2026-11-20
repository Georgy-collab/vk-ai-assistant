from __future__ import annotations

from vkbottle import Callback, Keyboard, KeyboardButtonColor, Text

from config.prompts import ROLE_TITLES, RoleMode
from models.entities import UserState


def main_menu_keyboard() -> str:
    kb = (
        Keyboard(inline=False)
        .add(Text("Новый диалог", {"cmd": "new_dialog"}), color=KeyboardButtonColor.POSITIVE)
        .add(Text("Список диалогов", {"cmd": "list_dialogs"}))
        .row()
        .add(Text("Сменить режим", {"cmd": "change_mode"}), color=KeyboardButtonColor.PRIMARY)
        .add(Text("Настройки", {"cmd": "settings"}))
        .row()
        .add(Text("Помощь", {"cmd": "help"}), color=KeyboardButtonColor.SECONDARY)
    )
    return kb.get_json()


def dialogs_keyboard(state: UserState) -> str:
    kb = Keyboard(inline=True)
    for i, dialog in enumerate(state.dialogs):
        prefix = "✓ " if dialog.id == state.active_dialog_id else ""
        label = f"{prefix}{dialog.title}"[:40]
        kb.add(Callback(label, {"cmd": "switch_dialog", "id": dialog.id}))
        kb.add(
            Callback("✏", {"cmd": "rename_dialog", "id": dialog.id}),
            color=KeyboardButtonColor.PRIMARY,
        )
        kb.add(
            Callback("🗑", {"cmd": "delete_dialog", "id": dialog.id}),
            color=KeyboardButtonColor.NEGATIVE,
        )
        if i < len(state.dialogs) - 1:
            kb.row()
    kb.row()
    kb.add(Callback("« В меню", {"cmd": "menu"}), color=KeyboardButtonColor.SECONDARY)
    return kb.get_json()


def settings_keyboard() -> str:
    kb = (
        Keyboard(inline=True)
        .add(Callback("Выбрать режим", {"cmd": "change_mode"}), color=KeyboardButtonColor.PRIMARY)
        .row()
        .add(Callback("Очистить историю", {"cmd": "clear_history"}), color=KeyboardButtonColor.NEGATIVE)
        .row()
        .add(Callback("Инфо о модели", {"cmd": "model_info"}))
        .row()
        .add(Callback("« В меню", {"cmd": "menu"}), color=KeyboardButtonColor.SECONDARY)
    )
    return kb.get_json()


def modes_keyboard() -> str:
    kb = Keyboard(inline=True)
    roles = list(RoleMode)
    for i, role in enumerate(roles):
        kb.add(
            Callback(ROLE_TITLES[role], {"cmd": "set_mode", "mode": role.value}),
            color=KeyboardButtonColor.PRIMARY,
        )
        if i < len(roles) - 1:
            kb.row()
    kb.row()
    kb.add(Callback("« Назад", {"cmd": "settings"}), color=KeyboardButtonColor.SECONDARY)
    return kb.get_json()


def welcome_text() -> str:
    return (
        "Привет! Я AI-помощник во ВКонтакте.\n\n"
        "Пишите сообщение — отвечу в текущем диалоге.\n"
        "Могу прислать готовый файл, если попросите "
        "(например: «сделай файл notes.txt с планом»).\n"
        "Кнопки ниже — диалоги и режимы общения."
    )


def help_text() -> str:
    return (
        "Как пользоваться:\n"
        "• Просто напишите вопрос — бот ответит с учётом истории активного диалога.\n"
        "• «Новый диалог» — чистый контекст.\n"
        "• «Список диалогов» — переключение, переименование и удаление.\n"
        "• «Сменить режим» — стиль ответа только для текущего диалога.\n"
        "• «Настройки» — режим, очистка истории, модель.\n"
        "• Можно попросить готовый файл, например: "
        "«сделай файл script.py с …» или «пришли заметки файлом notes.txt».\n\n"
        "История хранит до 100 сообщений; старые сжимаются в резюме."
    )
