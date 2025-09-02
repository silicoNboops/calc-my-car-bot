from __future__ import annotations

import logging.config
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from api.config.logging import LOGGING
from bot.config.bot import RUNNING_MODE, TELEGRAM_API_TOKEN, RunningMode
from bot.routers import router

logging.config.dictConfig(LOGGING)
logger = logging.getLogger(__name__)

bot = Bot(
    TELEGRAM_API_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)

dispatcher = Dispatcher(storage=MemoryStorage())
dispatcher.include_router(router)


async def set_bot_commands() -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="/start", description="Запуск / Сброс"),
            # BotCommand(command="/calc", description="Быстрый расчёт в одну строку"),
            # BotCommand(command="/cancel", description="Сбросить текущий визард"),
        ],
    )


@dispatcher.startup()
async def on_startup() -> None:
    await set_bot_commands()


def run_polling() -> None:
    dispatcher.run_polling(bot)


def run_webhook() -> None:
    msg = "Webhook mode is not implemented yet"
    raise NotImplementedError(msg)


if __name__ == "__main__":
    if RUNNING_MODE == RunningMode.LONG_POLLING:
        run_polling()
    elif RUNNING_MODE == RunningMode.WEBHOOK:
        run_webhook()
    else:
        logger.error("Unknown running mode")
        sys.exit(1)
