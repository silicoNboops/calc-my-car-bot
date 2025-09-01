from __future__ import annotations

import asyncio
import logging
import os
from typing import Iterable

from aiogram import Bot
from celery import shared_task
from django.db.models import Q

from api.calculator.services import get_default_currency_provider
from api.user.models import User
from bot.utils.formatting import format_rates_message

logger = logging.getLogger(__name__)


@shared_task(name="tasks.daily.send_daily_rates")
def send_daily_rates() -> None:
    """Ежедневная рассылка курсов валют в 09:30 по TIME_ZONE.

    Кому отправляем:
    - всем пользователям с непустым telegram_id
    - исключая пользователей с username == 'admin'

    Требуется переменная окружения:
    - TELEGRAM_API_TOKEN — токен бота
    """
    token = os.getenv("TELEGRAM_API_TOKEN", "").strip()
    if not token:
        logger.warning("Daily rates: TELEGRAM_API_TOKEN is not set; skipping")
        return

    # Получаем курсы один раз и формируем единый текст
    provider = get_default_currency_provider()
    rates = provider.get_rates()
    text = format_rates_message(rates)

    # Получаем список chat_ids
    chat_ids: list[int] = list(
        User.objects.filter(~Q(username="admin"), telegram_id__isnull=False)
        .values_list("telegram_id", flat=True)
        .iterator()
    )
    if not chat_ids:
        logger.info("Daily rates: no recipients found; nothing to send")
        return

    async def _send_all(ids: Iterable[int]) -> None:
        bot = Bot(token=token)
        sent = 0
        failed = 0
        try:
            for chat_id in ids:
                try:
                    await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
                    sent += 1
                except Exception as e:
                    failed += 1
                    logger.warning("Daily rates: failed to send to %s: %s", chat_id, e)
            logger.info("Daily rates: sent=%d failed=%d", sent, failed)
        finally:
            await bot.session.close()

    asyncio.run(_send_all(chat_ids))
