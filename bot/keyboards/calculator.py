from __future__ import annotations

from dataclasses import dataclass

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


@dataclass
class VehicleTypeCD(CallbackData, prefix="veh"):
    type: str


def vehicle_type_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    # Идентификаторы строго соответствуют VehicleType в api.calculator.services:
    # ["car", "quad", "snowmobile", "motorcycle"]
    builder.button(text="Легковой", callback_data=VehicleTypeCD(type="car").pack())
    builder.button(text="Снегоход", callback_data=VehicleTypeCD(type="snowmobile").pack())
    builder.button(text="Квадроцикл", callback_data=VehicleTypeCD(type="quad").pack())
    builder.button(text="Мотоцикл", callback_data=VehicleTypeCD(type="motorcycle").pack())
    builder.adjust(1)
    return builder.as_markup()
