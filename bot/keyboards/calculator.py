from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from api.calculator.choices import VehicleType


class VehicleTypeCD(CallbackData, prefix="veh"):
    type: str


def vehicle_type_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    # Строим кнопки из единого источника истины — Django TextChoices
    for value, label in VehicleType.choices:
        builder.button(text=str(label), callback_data=VehicleTypeCD(type=str(value)).pack())
    builder.adjust(1)
    return builder.as_markup()
