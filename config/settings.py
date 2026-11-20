from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Конфигурация приложения из .env."""

    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    vk_api_token: str = Field(validation_alias="VK_API_TOKEN")

    proxy_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("PROXY_API_KEY", "PROXI_API_KEY"),
    )

    proxy_gemini_base_url: str = Field(
        default="https://api.proxyapi.ru",
        validation_alias="PROXY_GEMINI_BASE_URL",
    )
    proxy_gemini_api_version: str = Field(
        default="v1beta",
        validation_alias="PROXY_GEMINI_API_VERSION",
    )
    gemini_model: str = Field(
        default="gemini-2.5-flash",
        validation_alias="GEMINI_MODEL",
    )

    users_dir: Path = Field(default=ROOT_DIR / "users")
    max_history_messages: int = Field(default=100, validation_alias="MAX_HISTORY_MESSAGES")
    max_user_message_length: int = Field(default=3500, validation_alias="MAX_USER_MESSAGE_LENGTH")
    max_vk_message_length: int = Field(default=4000, validation_alias="MAX_VK_MESSAGE_LENGTH")
    ai_timeout_seconds: float = Field(default=60.0, validation_alias="AI_TIMEOUT_SECONDS")
    summary_batch_size: int = Field(default=40, validation_alias="SUMMARY_BATCH_SIZE")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    @model_validator(mode="after")
    def _require_proxy_key(self) -> "Settings":
        if not self.proxy_api_key:
            raise ValueError("Укажите PROXY_API_KEY (или PROXI_API_KEY) в .env")
        return self

    @property
    def api_key(self) -> str:
        return self.proxy_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
