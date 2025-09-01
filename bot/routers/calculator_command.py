from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async

from api.calculator.services import (
    CalculatorService,
    EstimateInput,
    get_default_currency_provider,
)
from bot.utils.formatting import fmt_money
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


def _format_result(res) -> str:  # type: ignore[no-untyped-def]
    return (
        "🧮 Итог расчёта:\n"
        f"Цена (RUB): <b>{fmt_money(res.price_rub)}</b>\n"
        f"Цена (EUR): <b>{fmt_money(res.price_eur)}</b>\n"
        f"Пошлина (EUR): <b>{fmt_money(res.duty_eur)}</b>\n"
        f"Пошлина (RUB): <b>{fmt_money(res.duty_rub)}</b>\n"
        f"Утильсбор (RUB): <b>{fmt_money(res.util_fee)}</b>\n"
        f"Акциз (RUB): <b>{fmt_money(res.accise_rub)}</b>\n"
        f"НДС (RUB): <b>{fmt_money(res.vat_rub)}</b>\n"
        f"Таможенный сбор (RUB): <b>{fmt_money(res.customs_fee)}</b>\n"
        f"Всего (RUB): <b>{fmt_money(res.subtotal_customs)}</b>\n"
    )


def _estimate_sync(payload: dict) -> str:
    """Синхронная часть: берёт ORM-данные и считает результат."""
    service = CalculatorService(currency_provider=get_default_currency_provider())
    calc = service.build_calculator()
    res = calc.estimate(EstimateInput(**payload))
    return _format_result(res)


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
