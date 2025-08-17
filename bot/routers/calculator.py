from __future__ import annotations

import re
from typing import TYPE_CHECKING

from aiogram import Router, F
from aiogram.fsm.context import FSMContext

from bot.keyboards.calculator import (
    VehicleTypeCD,
    CurrencyCD,
    currency_kb,
    format_vehicle_title,
    format_currency_title,
    RoleCD,
    role_kb,
    format_role_title,
)
from bot.states import CalculatorState

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery, Message

router = Router()


@router.callback_query(CalculatorState.VEHICLE_TYPE, VehicleTypeCD.filter())
async def choose_vehicle_type(call: CallbackQuery, state: FSMContext, callback_data: VehicleTypeCD) -> None:
    # 1) Сохраняем выбранный тип ТС
    await state.update_data(vehicle_type=callback_data.type)
    # 2) Переходим к следующему шагу — выбор валюты
    await state.set_state(CalculatorState.CURRENCY)
    # 3) Редактируем текущее сообщение (не создаём новое), показываем клавиатуру валют
    veh_label = format_vehicle_title(callback_data.type)
    await call.message.edit_text(
        (
            "— Тип авто: <b>{veh}</b>\n\n"
            "Выберите, в какой валюте будет указана цена автомобиля:"
        ).format(veh=veh_label),
        reply_markup=currency_kb(),
    )
    await call.answer()


@router.callback_query(CalculatorState.CURRENCY, CurrencyCD.filter())
async def choose_currency(call: CallbackQuery, state: FSMContext, callback_data: CurrencyCD) -> None:
    # Сохраняем валюту и подтверждаем выбор
    await state.update_data(currency=callback_data.code)
    data = await state.get_data()
    vehicle_type = format_vehicle_title(str(data.get("vehicle_type", "")))
    currency_label = format_currency_title(callback_data.code)
    msg = await call.message.edit_text(
        (
            "Выбор сделан:\n"
            f"— Тип авто: <b>{vehicle_type}</b>\n"
            f"— Валюта: <b>{currency_label}</b>\n\n"
            "Введите стоимость автомобиля (например, 💰 1 200 000):"
        ),
        reply_markup=None,
    )
    # Переходим к вводу стоимости и запоминаем id сообщения с промптом
    await state.update_data(prompt_chat_id=msg.chat.id, prompt_message_id=msg.message_id, vehicle_title=vehicle_type,
                            currency_title=currency_label)
    await state.set_state(CalculatorState.PRICE)
    await call.answer()


def _parse_price(raw: str) -> int | None:
    """Парсит цену из строки, допускает любые пробелы, запятые и точки как разделители тысяч.

    Возвращает целое число (единицы валюты) или None, если невалидно.
    Ограничения: не пусто, неотрицательно, только цифры после очистки.
    """
    if raw is None:
        return None
    s = raw.strip()
    if not s:
        return None
    # Удаляем все пробелы (в т.ч. множественные), запятые и точки
    s = re.sub(r"[\s,\.]+", "", s)
    if not s or not s.isdigit():
        return None
    try:
        value = int(s)
    except ValueError:
        return None
    # Требование: строго > 0
    if value <= 0:
        return None
    return value


def _format_amount(value: int) -> str:
    """Форматирует число с пробелами в качестве разделителей тысяч."""
    return f"{value:,}".replace(",", " ")


@router.message(CalculatorState.PRICE, F.text)
async def input_price(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    chat_id = data.get("prompt_chat_id")
    msg_id = data.get("prompt_message_id")
    vehicle_title = data.get("vehicle_title")
    currency_title = data.get("currency_title")

    value = _parse_price(message.text or "")
    # Пытаемся удалить пользовательское сообщение (эстетика чата)
    try:
        await message.delete()
    except Exception:
        pass
    if value is None:
        # Определяем пояснение ошибки
        raw = (message.text or "").strip()
        if not raw:
            reason = "Ошибка: значение пустое."
        else:
            # Если после очистки не цифры — это не число; либо число <= 0
            cleaned = re.sub(r"[\s,\.]+", "", raw)
            if not cleaned.isdigit():
                reason = "Ошибка: введите целое число, можно с пробелами/запятыми/точками как разделителями тысяч."
            else:
                reason = "Ошибка: стоимость должна быть > 0."

        error_summary = (
            "Выбор сделан:\n"
            f"— Тип авто: <b>{vehicle_title}</b>\n"
            f"— Валюта: <b>{currency_title}</b>\n"
            f"— Стоимость: <b>💰 ОШИБКА</b>\n\n"
            f"{reason}"
        )
        if chat_id and msg_id:
            await message.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=error_summary)
        else:
            await message.answer(error_summary)
        return

    # Валидно — сохраняем
    await state.update_data(price=value)
    amount_fmt = _format_amount(value)
    prompt_text = (
        "Выбор сделан:\n"
        f"— Тип авто: <b>{vehicle_title}</b>\n"
        f"— Валюта: <b>{currency_title}</b>\n"
        f"— Стоимость: <b>💰 {amount_fmt}</b>\n\n"
        "Кто ввозит автомобиль:"
    )
    if chat_id and msg_id:
        await message.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=prompt_text, reply_markup=role_kb())
    else:
        await message.answer(prompt_text, reply_markup=role_kb())
    await state.set_state(CalculatorState.ROLE)


@router.callback_query(CalculatorState.ROLE, RoleCD.filter())
async def choose_role(call: CallbackQuery, state: FSMContext, callback_data: RoleCD) -> None:
    await state.update_data(role=callback_data.kind)
    data = await state.get_data()
    vehicle_title = data.get("vehicle_title") or format_vehicle_title(str(data.get("vehicle_type", "")))
    currency_title = data.get("currency_title") or format_currency_title(str(data.get("currency", "")))
    price = int(data.get("price", 0))
    amount_fmt = _format_amount(price)
    role_title = format_role_title(callback_data.kind)
    await call.message.edit_text(
        (
            "Выбор сделан:\n"
            f"— Тип авто: <b>{vehicle_title}</b>\n"
            f"— Валюта: <b>{currency_title}</b>\n"
            f"— Стоимость: <b>💰 {amount_fmt}</b>\n"
            f"— Кто ввозит: <b>{role_title}</b>\n\n"
            "Следующий шаг мастера добавлю далее."
        ),
        reply_markup=None,
    )
    await call.answer()
