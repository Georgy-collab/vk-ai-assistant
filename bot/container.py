from __future__ import annotations

from dataclasses import dataclass

from config.settings import Settings, get_settings
from services.ai.base import AIProvider
from services.ai.factory import create_ai_service
from services.chat_service import ChatService
from services.dialog_service import DialogService
from services.memory_service import MemoryService
from storage.json_storage import JsonUserStorage


@dataclass
class AppContainer:
    settings: Settings
    storage: JsonUserStorage
    dialogs: DialogService
    memory: MemoryService
    ai: AIProvider
    chat: ChatService


def build_container() -> AppContainer:
    settings = get_settings()
    storage = JsonUserStorage(settings.users_dir)
    dialogs = DialogService(storage)
    ai = create_ai_service(settings)
    memory = MemoryService(settings, ai)
    chat = ChatService(settings=settings, dialogs=dialogs, memory=memory, ai=ai)
    return AppContainer(
        settings=settings,
        storage=storage,
        dialogs=dialogs,
        memory=memory,
        ai=ai,
        chat=chat,
    )
