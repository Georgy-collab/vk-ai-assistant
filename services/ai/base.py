from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from models.entities import ChatMessage, GeneratedFile


@dataclass(slots=True)
class AIResponse:
    text: str
    model: str
    finish_reason: str | None = None
    files: list[GeneratedFile] = field(default_factory=list)


class AIProvider(ABC):
    """Абстракция LLM-провайдера — легко подключить другую модель."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    async def generate(
        self,
        *,
        system_prompt: str,
        history: list[ChatMessage],
        user_message: str,
    ) -> AIResponse:
        raise NotImplementedError

    @abstractmethod
    async def summarize(self, *, messages: list[ChatMessage]) -> str:
        raise NotImplementedError
