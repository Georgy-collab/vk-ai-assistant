from __future__ import annotations

import logging
import re
from pathlib import PurePosixPath

from models.entities import GeneratedFile

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {
    ".txt",
    ".md",
    ".py",
    ".js",
    ".ts",
    ".json",
    ".csv",
    ".html",
    ".css",
    ".sql",
    ".xml",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".log",
    ".sh",
    ".bat",
    ".ps1",
}

MAX_FILENAME_LEN = 64
MAX_FILE_BYTES = 200_000  # ~200 KB текста — комфортно для сообщений VK


class DocumentService:
    """Подготовка файлов к отправке (без VK)."""

    def prepare(self, files: list[GeneratedFile]) -> list[tuple[str, bytes]]:
        prepared: list[tuple[str, bytes]] = []
        for item in files:
            try:
                filename = self._sanitize_filename(item.filename)
                data = item.content.encode("utf-8")
                if len(data) > MAX_FILE_BYTES:
                    logger.warning("Файл %s слишком большой (%s байт), обрезаю", filename, len(data))
                    data = data[:MAX_FILE_BYTES]
                prepared.append((filename, data))
            except ValueError as exc:
                logger.warning("Пропуск файла %s: %s", item.filename, exc)
        return prepared

    def _sanitize_filename(self, name: str) -> str:
        raw = PurePosixPath(name.replace("\\", "/")).name.strip()
        raw = re.sub(r"[^\w.\- ()а-яА-ЯёЁ]+", "_", raw, flags=re.UNICODE)
        raw = raw.strip(" ._")
        if not raw:
            raise ValueError("пустое имя файла")
        if "." not in raw:
            raw = f"{raw}.txt"
        suffix = PurePosixPath(raw).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise ValueError(f"расширение {suffix} не разрешено")
        stem = PurePosixPath(raw).stem[: MAX_FILENAME_LEN - len(suffix)]
        if not stem:
            raise ValueError("пустое имя файла")
        return f"{stem}{suffix}"
