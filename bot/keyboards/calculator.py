from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from api.calculator.choices import VehicleType, Currency

# Человекочитаемые названия валют для отображения в кнопках
_CURRENCY_TITLES_RU: dict[str, str] = {
    "CNY": "Юань",
    "JPY": "Иена",
    "KRW": "Вона",
    "USD": "Доллар",
    "EUR": "Евро",
    "RUB": "Рубль",
}


class VehicleTypeCD(CallbackData, prefix="veh"):
    type: str


def vehicle_type_kb() -> InlineKeyboardMarkup:
    
    builder = InlineKeyboardBuilder()
    # Строим кнопки из единого источника истины — Django TextChoices
    for value, label in VehicleType.choices:
        builder.button(text=str(label), callback_data=VehicleTypeCD(type=str(value)).pack())
    builder.adjust(1)
    return builder.as_markup()


class CurrencyCD(CallbackData, prefix="cur"):
    code: str


def currency_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for value, label in Currency.choices:
        title = _CURRENCY_TITLES_RU.get(str(value), str(label))
        builder.button(text=title, callback_data=CurrencyCD(code=str(value)).pack())
    builder.adjust(1)
    return builder.as_markup()
