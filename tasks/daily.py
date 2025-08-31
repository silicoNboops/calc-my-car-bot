from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot
from celery import shared_task

from api.calculator.services import get_default_currency_provider
from bot.utils.formatting import format_rates_message

logger = logging.getLogger(__name__)


@shared_task(name="tasks.daily.send_daily_rates")
def send_daily_rates() -> None:
    """Ежедневная рассылка курсов валют в 09:30 по TIME_ZONE.

    Требуются переменные окружения:
    - TELEGRAM_API_TOKEN — токен бота
    - RATES_BROADCAST_CHAT_ID — chat_id или @channel_username для отправки
    """
    token = os.getenv("TELEGRAM_API_TOKEN", "").strip()
    chat_id = os.getenv("RATES_BROADCAST_CHAT_ID", "").strip()

    if not token or not chat_id:
        logger.warning(
            "Daily rates: TELEGRAM_API_TOKEN or RATES_BROADCAST_CHAT_ID is not set; skipping"
        )
        return

    # 1) Получаем курсы и форматируем сообщение так же, как при нажатии кнопки
    provider = get_default_currency_provider()
    rates = provider.get_rates()
    text = format_rates_message(rates)

    # 2) Отправляем через aiogram (асинхронный клиент) из Celery-задачи
    async def _send() -> None:
        bot = Bot(token=token)
        try:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
        finally:
            await bot.session.close()

    asyncio.run(_send())
