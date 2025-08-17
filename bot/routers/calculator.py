from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import Router, F
from aiogram.fsm.context import FSMContext

from bot.keyboards.calculator import VehicleTypeCD
from bot.states import CalculatorState

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery

router = Router()


@router.callback_query(CalculatorState.VEHICLE_TYPE, VehicleTypeCD.filter())
async def choose_vehicle_type(call: CallbackQuery, state: FSMContext, callback_data: VehicleTypeCD) -> None:
    # Сохраняем выбранный тип ТС в FSM
    await state.update_data(vehicle_type=callback_data.type)
    # Пока только подтверждаем выбор; следующие шаги добавим позже
    await call.message.edit_text(
        f"Вы выбрали тип: <b>{callback_data.type}</b>\nСледующие шаги мастера скоро добавлю.",
    )
    await call.answer()
