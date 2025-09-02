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
    """Ежедневная публикация курсов валют в канал в 09:30 по TIME_ZONE.

    Отправляем ТОЛЬКО в канал (без рассылки пользователям).

    Требуются переменные окружения:
    - TELEGRAM_API_TOKEN — токен бота
    - TELEGRAM_RATES_CHANNEL — @username канала или числовой ID (-100...)
    """
    token = os.getenv("TELEGRAM_API_TOKEN", "").strip()
    if not token:
        logger.warning("Daily rates: TELEGRAM_API_TOKEN is not set; skipping")
        return

    channel_raw = os.getenv("TELEGRAM_RATES_CHANNEL", "").strip()
    if not channel_raw:
        logger.warning("Daily rates: TELEGRAM_RATES_CHANNEL is not set; skipping")
        return

    # Получаем курсы один раз и формируем единый текст
    provider = get_default_currency_provider()
    rates = provider.get_rates()
    text = format_rates_message(rates)

    # Разрешаем и @username, и числовой ID как строку;
    # если это число, безопасно конвертируем в int.
    chat_id: int | str = channel_raw
    if channel_raw.lstrip("-").isdigit():
        try:
            chat_id = int(channel_raw)
        except Exception:
            chat_id = channel_raw

    async def _send_once() -> None:
        bot = Bot(token=token)
        try:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
            logger.info("Daily rates: sent to channel %s", channel_raw)
        except Exception as e:
            logger.error("Daily rates: failed to send to channel %s: %s", channel_raw, e)
        finally:
            await bot.session.close()

    asyncio.run(_send_once())
