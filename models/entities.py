from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from config.prompts import RoleMode


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str
    timestamp: str = Field(default_factory=utc_now_iso)
    is_summary: bool = False


class GeneratedFile(BaseModel):
    """Текстовый файл, который бот отправит вложением во ВКонтакте."""

    filename: str
    content: str


class Dialog(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    title: str = "Новый диалог"
    mode: RoleMode = RoleMode.ASSISTANT
    messages: list[ChatMessage] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()


class UserSettings(BaseModel):
    default_mode: RoleMode = RoleMode.ASSISTANT
    pending_action: str | None = None
    pending_dialog_id: str | None = None


class UserState(BaseModel):
    user_id: int
    active_dialog_id: str
    dialogs: list[Dialog] = Field(default_factory=list)
    settings: UserSettings = Field(default_factory=UserSettings)

    def get_dialog(self, dialog_id: str) -> Dialog | None:
        for dialog in self.dialogs:
            if dialog.id == dialog_id:
                return dialog
        return None

    def get_active_dialog(self) -> Dialog:
        dialog = self.get_dialog(self.active_dialog_id)
        if dialog is None:
            if not self.dialogs:
                dialog = Dialog(title="Диалог 1")
                self.dialogs.append(dialog)
            else:
                dialog = self.dialogs[0]
            self.active_dialog_id = dialog.id
        return dialog

    def to_storage_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
