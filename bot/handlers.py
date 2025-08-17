from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.filters import Command

from api.user.models import User
from asgiref.sync import sync_to_async
from api.calculator.services import (
    CalculatorService,
    get_default_currency_provider,
    EstimateInput,
)
from bot.keyboards.start import start_menu_kb

if TYPE_CHECKING:
    from aiogram.types import Message

router = Router()


@router.message(Command(commands=["start"]))
async def handle_start_command(message: Message) -> None:
    if message.from_user is None:
        return

    _, is_new = await User.objects.aget_or_create(
        pk=message.from_user.id,
        defaults={
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name,
        },
    )
    # Приветствие + стартовое меню
    # Требование: "Вас приветствует ChinaMotorsBot!" и кнопки как на скрине
    base = "Вас приветствует ChinaMotorsBot!"
    extra = (
        "\nВы успешно зарегистрированы в боте." if is_new else "\nРады видеть вас снова."
    )
    await message.answer(base + extra, reply_markup=start_menu_kb())


@router.message(Command(commands=["id"]))
async def handle_id_command(message: Message) -> None:
    if message.from_user is None:
        return

    await message.answer(
        f"User Id: <b>{message.from_user.id}</b>\nChat Id: <b>{message.chat.id}</b>",
    )


def _parse_calc_args(text: str) -> dict | str:
    """Парсинг аргументов из сообщения.

    Ожидаемый формат (через пробел):
    /calc <price> <currency: EUR|USD|RUB|CNY|JPY|KRW> <engine_cc> <hp> <engine_type: Бензин|Дизель> <age_key: under_3|3_to_5|5_to_7|over_7|over_5> [jur|phys] [personal|commercial]

    Примеры:
    /calc 20000 EUR 1999 150 Бензин under_3 phys personal
    /calc 15000 EUR 2200 180 Бензин 3_to_5 jur commercial
    """
    parts = text.strip().split()
    if len(parts) < 7:
        return (
            "Неверный формат. Пример: \n"
            "/calc 20000 EUR 1999 150 Бензин under_3 phys personal"
        )

    try:
        _, price, currency, engine_cc, hp, engine_type, age_key, *rest = parts
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
        return (
            "Не удалось распарсить аргументы. Пример: \n"
            "/calc 20000 EUR 1999 150 Бензин under_3 phys personal"
        )


def _format_result(res) -> str:  # type: ignore[no-untyped-def]
    return (
        "Итог расчёта:\n"
        f"Цена (RUB): <b>{res.price_rub:,.2f}</b>\n"
        f"Цена (EUR): <b>{res.price_eur:,.2f}</b>\n"
        f"Пошлина (EUR): <b>{res.duty_eur:,.2f}</b>\n"
        f"Пошлина (RUB): <b>{res.duty_rub:,.2f}</b>\n"
        f"Утильсбор (RUB): <b>{res.util_fee:,.2f}</b>\n"
        f"Акциз (RUB): <b>{res.accise_rub:,.2f}</b>\n"
        f"НДС (RUB): <b>{res.vat_rub:,.2f}</b>\n"
        f"Таможенный сбор (RUB): <b>{res.customs_fee:,.2f}</b>\n"
        f"Всего (RUB): <b>{res.subtotal_customs:,.2f}</b>\n"
    )


def _estimate_sync(payload: dict) -> dict:
    """Синхронная часть: берёт ORM-данные и считает результат."""
    service = CalculatorService(currency_provider=get_default_currency_provider())
    calc = service.build_calculator()
    res = calc.estimate(EstimateInput(**payload))
    return _format_result(res)


@router.message(Command(commands=["calc"]))
async def handle_calc_command(message: Message) -> None:
    if message.text is None:
        await message.answer("Сообщение пустое. Пример: /calc 20000 EUR 1999 150 Бензин under_3 phys personal")
        return

    parsed = _parse_calc_args(message.text)
    if isinstance(parsed, str):
        await message.answer(parsed)
        return

    try:
        # Важно: доступ к ORM обёрнут через sync_to_async
        result_text = await sync_to_async(_estimate_sync)(parsed)
        await message.answer(result_text)
    except Exception as e:  # noqa: BLE001
        await message.answer(f"Ошибка расчёта: {e}")
