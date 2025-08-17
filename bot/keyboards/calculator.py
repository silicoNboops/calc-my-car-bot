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

# Эмодзи для валют (флаги). Используем перед текстом для лучшей читаемости
_CURRENCY_FLAGS: dict[str, str] = {
    "CNY": "🇨🇳",
    "JPY": "🇯🇵",
    "KRW": "🇰🇷",
    "USD": "🇺🇸",
    "EUR": "🇪🇺",
    "RUB": "🇷🇺",
}

# Эмодзи для видов ТС (только в клавиатурах)
_VEHICLE_EMOJI: dict[str, str] = {
    VehicleType.CAR.value: "🚗",
    VehicleType.SNOWMOBILE.value: "🛷",
    VehicleType.QUAD.value: "🛞",
    VehicleType.MOTORCYCLE.value: "🏍️",
}


class VehicleTypeCD(CallbackData, prefix="veh"):
    type: str


def vehicle_type_kb() -> InlineKeyboardMarkup:
    
    builder = InlineKeyboardBuilder()
    # Строим кнопки из единого источника истины — Django TextChoices
    for value, label in VehicleType.choices:
        emoji = _VEHICLE_EMOJI.get(str(value), "")
        text = f"{emoji} {label}".strip()
        builder.button(text=text, callback_data=VehicleTypeCD.pack(str(value)))
    builder.adjust(1)
    return builder.as_markup()


class CurrencyCD(CallbackData, prefix="cur"):
    code: str


def currency_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for value, label in Currency.choices:
        code = str(value)
        title = _CURRENCY_TITLES_RU.get(code, str(label))
        flag = _CURRENCY_FLAGS.get(code, "")
        text = f"{flag} {title}".strip()
        builder.button(text=text, callback_data=CurrencyCD.pack(code))
    builder.adjust(1)
    return builder.as_markup()
