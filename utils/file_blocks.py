from __future__ import annotations

import re

from models.entities import GeneratedFile

FILE_BLOCK_RE = re.compile(
    r"<<<VK_FILE\s+name=\"([^\"]+)\"\s*>>>\r?\n?(.*?)\r?\n?<<<END_VK_FILE>>>",
    re.DOTALL | re.IGNORECASE,
)

FILE_REQUEST_HINTS = (
    "файл",
    "файлом",
    "документом",
    "document",
    "скачай",
    "скачать",
    "пришли файл",
    "отправь файл",
    "сделай файл",
    "сохрани в файл",
    "в виде файла",
    ".txt",
    ".md",
    ".py",
    ".json",
    ".csv",
    ".html",
    ".css",
    ".js",
    ".sql",
    ".yaml",
    ".yml",
    ".xml",
    ".toml",
)


def user_asks_for_file(text: str) -> bool:
    lowered = text.lower()
    return any(hint in lowered for hint in FILE_REQUEST_HINTS)


def extract_file_blocks(raw_text: str) -> tuple[str, list[GeneratedFile]]:
    """Достаёт файлы из ответа модели и возвращает очищенный текст для чата."""
    files: list[GeneratedFile] = []
    for match in FILE_BLOCK_RE.finditer(raw_text):
        filename = match.group(1).strip()
        content = match.group(2)
        if filename and content.strip():
            files.append(GeneratedFile(filename=filename, content=content))

    cleaned = FILE_BLOCK_RE.sub("", raw_text).strip()
    if files and not cleaned:
        names = ", ".join(f.filename for f in files)
        cleaned = f"Готово — отправляю файл: {names}."
    return cleaned, files


def history_text_for_files(chat_text: str, files: list[GeneratedFile]) -> str:
    if not files:
        return chat_text
    names = ", ".join(f.filename for f in files)
    suffix = f"\n[Отправлен файл: {names}]"
    return f"{chat_text}{suffix}".strip()
