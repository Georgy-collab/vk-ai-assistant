from __future__ import annotations

import re

from vkbottle.tools import markdown
from vkbottle.tools.formatting import Format


def sanitize_user_text(text: str | None, max_length: int) -> str | None:
    """Возвращает очищенный текст или None, если сообщение пустое/невалидное."""
    if text is None:
        return None
    cleaned = text.strip()
    if not cleaned:
        return None
    if len(cleaned) > max_length:
        return cleaned[:max_length]
    return cleaned


def chunk_text(text: str, max_length: int) -> list[str]:
    """Делит длинный ответ на части под лимит VK."""
    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= max_length:
            chunks.append(remaining)
            break
        cut = remaining.rfind("\n", 0, max_length)
        if cut < max_length // 2:
            cut = remaining.rfind(" ", 0, max_length)
        if cut < max_length // 2:
            cut = max_length
        chunks.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()
    return chunks


_HEADER_RE = re.compile(r"(?m)^#{1,6}\s+")
_CODE_FENCE_RE = re.compile(r"```[\w+-]*\n?|```")


def _normalize_llm_markdown(text: str) -> str:
    """Убирает разметку, которую VK не умеет (заголовки, code fences)."""
    cleaned = _CODE_FENCE_RE.sub("", text)
    cleaned = _HEADER_RE.sub("", cleaned)
    return cleaned.strip()


def prepare_vk_message_parts(text: str, max_length: int) -> list[str | Format]:
    """Конвертирует Markdown LLM → VK Format и режет по лимиту сообщения.

    VK не рендерит сырой `**bold**` / `*italic*` — нужен format_data через
    vkbottle.tools.markdown. Длинные ответы уходят уже очищенным текстом.
    """
    normalized = _normalize_llm_markdown(text)
    formatted = markdown(normalized)
    plain = str(formatted)
    if len(plain) <= max_length:
        return [formatted]
    return chunk_text(plain, max_length)
