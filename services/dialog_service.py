from __future__ import annotations

from config.prompts import ROLE_TITLES, RoleMode, get_role_title
from models.entities import Dialog, UserState
from storage.json_storage import JsonUserStorage


class DialogService:
    """Менеджер диалогов и настроек пользователя."""

    def __init__(self, storage: JsonUserStorage) -> None:
        self._storage = storage

    async def get_or_create_user(self, user_id: int) -> UserState:
        return await self._storage.load(user_id)

    async def save(self, state: UserState) -> None:
        await self._storage.save(state)

    async def create_dialog(self, user_id: int, title: str | None = None) -> UserState:
        state = await self.get_or_create_user(user_id)
        index = len(state.dialogs) + 1
        dialog = Dialog(
            title=title or f"Диалог {index}",
            mode=state.settings.default_mode,
        )
        state.dialogs.append(dialog)
        state.active_dialog_id = dialog.id
        await self.save(state)
        return state

    async def switch_dialog(self, user_id: int, dialog_id: str) -> UserState | None:
        state = await self.get_or_create_user(user_id)
        dialog = state.get_dialog(dialog_id)
        if dialog is None:
            return None
        state.active_dialog_id = dialog_id
        await self.save(state)
        return state

    async def rename_dialog(self, user_id: int, dialog_id: str, title: str) -> UserState | None:
        state = await self.get_or_create_user(user_id)
        dialog = state.get_dialog(dialog_id)
        if dialog is None:
            return None
        dialog.title = title.strip()[:64] or dialog.title
        dialog.touch()
        state.settings.pending_action = None
        state.settings.pending_dialog_id = None
        await self.save(state)
        return state

    async def delete_dialog(self, user_id: int, dialog_id: str) -> UserState | None:
        state = await self.get_or_create_user(user_id)
        if len(state.dialogs) <= 1:
            return None

        state.dialogs = [d for d in state.dialogs if d.id != dialog_id]
        if state.active_dialog_id == dialog_id:
            state.active_dialog_id = state.dialogs[0].id
        await self.save(state)
        return state

    async def set_mode(self, user_id: int, mode: RoleMode, *, for_active: bool = True) -> UserState:
        state = await self.get_or_create_user(user_id)
        state.settings.default_mode = mode
        if for_active:
            dialog = state.get_active_dialog()
            dialog.mode = mode
            dialog.touch()
        await self.save(state)
        return state

    async def set_pending(self, user_id: int, action: str | None, dialog_id: str | None = None) -> UserState:
        state = await self.get_or_create_user(user_id)
        state.settings.pending_action = action
        state.settings.pending_dialog_id = dialog_id
        await self.save(state)
        return state

    async def clear_pending(self, user_id: int) -> UserState:
        return await self.set_pending(user_id, None, None)

    def format_dialogs_list(self, state: UserState) -> str:
        lines = ["Ваши диалоги:"]
        for dialog in state.dialogs:
            mark = "✓" if dialog.id == state.active_dialog_id else "•"
            mode_title = get_role_title(dialog.mode)
            lines.append(f"{mark} {dialog.title} [{mode_title}] — {len(dialog.messages)} сообщ.")
        return "\n".join(lines)

    def format_status(self, state: UserState, model_name: str) -> str:
        dialog = state.get_active_dialog()
        return (
            f"Активный диалог: {dialog.title}\n"
            f"Режим: {ROLE_TITLES[dialog.mode]}\n"
            f"Сообщений в истории: {len(dialog.messages)}\n"
            f"Модель: {model_name}"
        )
