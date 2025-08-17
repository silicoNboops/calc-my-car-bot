from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from api.calculator.choices import VehicleType, Currency, ImporterKind, EngineType

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
        builder.button(text=text, callback_data=VehicleTypeCD(type=str(value)).pack())
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
        builder.button(text=text, callback_data=CurrencyCD(code=code).pack())
    builder.adjust(1)
    return builder.as_markup()


# Helpers for readable titles (emoji + text) for summaries
def format_vehicle_title(value: str) -> str:
    label = dict(VehicleType.choices).get(value, value)
    emoji = _VEHICLE_EMOJI.get(value, "")
    return f"{emoji} {label}".strip()


def format_currency_title(code: str) -> str:
    title = _CURRENCY_TITLES_RU.get(code, dict(Currency.choices).get(code, code))
    flag = _CURRENCY_FLAGS.get(code, "")
    return f"{flag} {title}".strip()


# ROLE (кто ввозит): физ/юр
class RoleCD(CallbackData, prefix="role"):
    kind: str  # jur | phys_personal | phys_commercial


# Базовые подписи берём из ImporterKind.choices, переопределять не нужно
_ROLE_TITLES: dict[str, str] = dict(ImporterKind.choices)

_ROLE_EMOJI: dict[str, str] = {
    "jur": "🏢",
    "phys_personal": "👤",
    "phys_commercial": "🛒",
}


def role_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for kind, title in ImporterKind.choices:
        emoji = _ROLE_EMOJI.get(kind, "")
        text = f"{emoji} {title}".strip()
        builder.button(text=text, callback_data=RoleCD(kind=kind).pack())
    builder.adjust(1)
    return builder.as_markup()


def format_importer_kind_title(kind: str) -> str:
    title = _ROLE_TITLES.get(kind, dict(ImporterKind.choices).get(kind, kind))
    emoji = _ROLE_EMOJI.get(kind, "")
    return f"{emoji} {title}".strip()


# ENGINE TYPE
class EngineTypeCD(CallbackData, prefix="eng"):
    kind: str  # values from EngineType choices


_ENGINE_EMOJI: dict[str, str] = {
    EngineType.BENZIN: "🛢️",
    EngineType.DIESEL: "🛢️",
    EngineType.ELECTRO: "⚡",
    EngineType.HYBRID_PARALLEL: "♻️",
    EngineType.HYBRID_SERIES: "♻️",
}


def engine_type_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for kind, title in EngineType.choices:
        emoji = _ENGINE_EMOJI.get(kind, "")
        text = f"{emoji} {title}".strip()
        builder.button(text=text, callback_data=EngineTypeCD(kind=kind).pack())
    builder.adjust(1)
    return builder.as_markup()


def format_engine_type_title(kind: str) -> str:
    title = dict(EngineType.choices).get(kind, kind)
    emoji = _ENGINE_EMOJI.get(kind, "")
    return f"{emoji} {title}".strip()
