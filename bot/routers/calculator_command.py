from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async

from api.calculator.models import Settings
from api.calculator.services import (
    CalculatorService,
    EstimateInput,
    get_default_currency_provider,
)
from bot.utils.formatting import format_result_block_rub_only
from bot.utils.strings import (
    CALC_USAGE_HELP,
    CALC_PARSE_ERROR,
    CALC_EMPTY_MESSAGE,
)

if TYPE_CHECKING:
    from aiogram.types import Message

router = Router()


def _parse_calc_args(text: str) -> dict | str:
    """Парсинг аргументов из сообщения.

    Ожидаемый формат (через пробел):
    /calc <price> <currency: EUR|USD|RUB|CNY|JPY|KRW> <engine_cc> <hp> <engine_type: Бензин|Дизель> <age_key: under_3|3_to_5|5_to_7|over_7> [jur|phys] [personal|commercial]

    Примеры:
    /calc 20000 EUR 1999 150 Бензин under_3 phys personal
    /calc 15000 EUR 2200 180 Бензин 3_to_5 jur commercial
    """
    parts = text.strip().split()
    if len(parts) < 7:
        return CALC_USAGE_HELP

    try:
        _, price, currency, engine_cc, hp, engine_type, age_key, *rest = parts
        # Backward-compat: normalize legacy 'over_5' to '5_to_7'
        if age_key == "over_5":
            age_key = "5_to_7"
        is_jur = False
        is_personal_use = True
        if rest:
            role = rest[0].lower()
            if role in ("jur", "corp", "biz"):
                is_jur = True
            elif role in ("phys", "pers", "user"):
                is_jur = False
        if len(rest) >= 2:
            use = rest[1].lower()
            if use in ("personal", "pers"):
                is_personal_use = True
            elif use in ("commercial", "comm"):
                is_personal_use = False

        return {
            "price": float(price),
            "currency": currency.upper(),
            "engine_cc": int(engine_cc),
            "hp": int(hp),
            "engine_type": engine_type,
            "age_key": age_key,
            "is_jur": is_jur,
            "is_personal_use": is_personal_use,
        }
    except Exception:
        return CALC_PARSE_ERROR


def _get_company_commission_rub() -> float:
    """Читает комиссию компании (руб) из Settings с нормализацией тысяч."""
    s = Settings.objects.order_by("-updated_at").first()
    raw = float(getattr(s, "company_commission_rub", 0.0) or 0.0)
    if raw < 1000.0:
        return raw * 1000.0
    return raw


def _get_broker_service_fee_rub() -> float:
    """Фиксированная стоимость услуг брокера (оформление).

    Пока задаём константой 69 000 ₽. При необходимости в будущем
    можно вынести в Settings и админку.
    """
    return 69000.0


def _estimate_sync(payload: dict) -> str:
    """Синхронная часть: берёт ORM-данные и считает результат."""
    service = CalculatorService(currency_provider=get_default_currency_provider())
    calc = service.build_calculator()
    res = calc.estimate(EstimateInput(**payload))
    values = {
        "price_rub": float(res.price_rub),
        "duty_rub": float(res.duty_rub),
        "util_fee": float(res.util_fee),
        "accise_rub": float(res.accise_rub),
        "vat_rub": float(res.vat_rub),
        "customs_fee": float(res.customs_fee),
        "subtotal_customs": float(res.subtotal_customs),
    }
    commission = _get_company_commission_rub()
    broker_fee = _get_broker_service_fee_rub()
    return format_result_block_rub_only(
        values,
        commission_rub=commission,
        broker_fee_rub=broker_fee,
    )


@router.message(Command(commands=["calc"]))
async def handle_calc_command(message: Message, state: FSMContext) -> None:
    # Сброс состояния визарда при вызове /calc
    await state.clear()
    if message.text is None:
        await message.answer(CALC_EMPTY_MESSAGE)
        return

    parsed = _parse_calc_args(message.text)
    if isinstance(parsed, str):
        await message.answer(parsed)
        return

    try:
        result_text = await sync_to_async(_estimate_sync)(parsed)
        await message.answer(result_text)
    except Exception as e:  # noqa: BLE001
        await message.answer(f"Ошибка расчёта: {e}")
