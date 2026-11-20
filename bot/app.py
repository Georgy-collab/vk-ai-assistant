from __future__ import annotations

import logging

from vkbottle.bot import Bot

from bot.container import AppContainer, build_container
from bot.handlers import register_callback_handlers, register_message_handlers
from utils.logging import setup_logging

logger = logging.getLogger(__name__)


def create_bot(container: AppContainer | None = None) -> Bot:
    container = container or build_container()
    setup_logging(container.settings.log_level)

    bot = Bot(token=container.settings.vk_api_token)
    register_callback_handlers(bot, container)
    register_message_handlers(bot, container)

    logger.info(
        "Бот инициализирован. Модель=%s base=%s",
        container.chat.model_name,
        container.settings.proxy_gemini_base_url,
    )
    return bot


async def _warmup_group_id(bot: Bot) -> None:
    """Кладём id сообщества в bot.state — нужен для messages.setActivity."""
    try:
        groups = await bot.api.groups.get_by_id()
        items = getattr(groups, "groups", None) or groups
        if items:
            group = items[0]
            bot.state.group_id = int(group.id)
            logger.info("group_id сообщества: %s", bot.state.group_id)
    except Exception:
        logger.warning("Не удалось получить group_id сообщества", exc_info=True)


def run() -> None:
    bot = create_bot()
    bot.startup_tasks.append(_warmup_group_id(bot))
    bot.run()
