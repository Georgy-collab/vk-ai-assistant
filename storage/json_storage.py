from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

import aiofiles
import aiofiles.os

from models.entities import Dialog, UserState

logger = logging.getLogger(__name__)


class JsonUserStorage:
    """Асинхронное JSON-хранилище: один файл на пользователя."""

    def __init__(self, users_dir: Path) -> None:
        self._users_dir = users_dir
        self._locks: dict[int, asyncio.Lock] = {}

    def _path(self, user_id: int) -> Path:
        return self._users_dir / f"{user_id}.json"

    def _lock_for(self, user_id: int) -> asyncio.Lock:
        if user_id not in self._locks:
            self._locks[user_id] = asyncio.Lock()
        return self._locks[user_id]

    async def ensure_dir(self) -> None:
        await aiofiles.os.makedirs(self._users_dir, exist_ok=True)

    async def load(self, user_id: int) -> UserState:
        await self.ensure_dir()
        path = self._path(user_id)
        async with self._lock_for(user_id):
            if not path.exists():
                state = self._create_default(user_id)
                await self._write_unlocked(path, state)
                logger.info("Создан профиль пользователя %s", user_id)
                return state

            async with aiofiles.open(path, "r", encoding="utf-8") as file:
                raw = await file.read()
            data = json.loads(raw)
            return UserState.model_validate(data)

    async def save(self, state: UserState) -> None:
        await self.ensure_dir()
        path = self._path(state.user_id)
        async with self._lock_for(state.user_id):
            await self._write_unlocked(path, state)

    async def _write_unlocked(self, path: Path, state: UserState) -> None:
        payload = json.dumps(state.to_storage_dict(), ensure_ascii=False, indent=2)
        tmp_path = path.with_suffix(".tmp")
        async with aiofiles.open(tmp_path, "w", encoding="utf-8") as file:
            await file.write(payload)
        await aiofiles.os.replace(tmp_path, path)

    @staticmethod
    def _create_default(user_id: int) -> UserState:
        dialog = Dialog(title="Диалог 1")
        return UserState(
            user_id=user_id,
            active_dialog_id=dialog.id,
            dialogs=[dialog],
        )
