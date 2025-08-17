from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import Router, F
from aiogram.fsm.context import FSMContext

from bot.keyboards.calculator import (
    VehicleTypeCD,
    CurrencyCD,
    currency_kb,
    format_vehicle_title,
    format_currency_title,
)
from bot.states import CalculatorState
from api.calculator.choices import VehicleType

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery

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
    await call.message.edit_text(
        (
            "Выбор сделан:\n"
            f"— Тип авто: <b>{vehicle_type}</b>\n"
            f"— Валюта: <b>{currency_label}</b>\n\n"
            "Следующий шаг мастера добавлю далее."
        ),
        reply_markup=None,
    )
    await call.answer()
