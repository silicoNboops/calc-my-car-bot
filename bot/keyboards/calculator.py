from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from api.calculator.choices import VehicleType, Currency, ImporterKind, EngineType, AgeKey
from bot.utils.currency import format_currency_title

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
        text = format_currency_title(code)
        builder.button(text=text, callback_data=CurrencyCD(code=code).pack())
    builder.adjust(1)
    return builder.as_markup()


# Helpers for readable titles (emoji + text) for summaries
def format_vehicle_title(value: str) -> str:
    label = dict(VehicleType.choices).get(value, value)
    emoji = _VEHICLE_EMOJI.get(value, "")
    return f"{emoji} {label}".strip()


# ROLE (кто ввозит): физ/юр
class RoleCD(CallbackData, prefix="role"):
    kind: str  # jur | phys_personal | phys_commercial


# Базовые подписи берём из ImporterKind.choices, переопределять не нужно
_IMPORTER_KIND_TITLES: dict[str, str] = dict(ImporterKind.choices)

_IMPORTER_KIND_EMOJI: dict[str, str] = {
    "jur": "🏢",
    "phys_personal": "👤",
    "phys_commercial": "🛒",
}


def role_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for kind, title in ImporterKind.choices:
        emoji = _IMPORTER_KIND_EMOJI.get(kind, "")
        text = f"{emoji} {title}".strip()
        builder.button(text=text, callback_data=RoleCD(kind=kind).pack())
    builder.adjust(1)
    return builder.as_markup()


def format_importer_kind_title(kind: str) -> str:
    title = _IMPORTER_KIND_TITLES.get(kind, dict(ImporterKind.choices).get(kind, kind))
    emoji = _IMPORTER_KIND_EMOJI.get(kind, "")
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


# AGE KEY
class AgeKeyCD(CallbackData, prefix="age"):
    key: str  # values from AgeKey choices


_AGE_EMOJI: dict[str, str] = {
    AgeKey.UNDER_3: "🟢",
    AgeKey.FROM_3_TO_5: "🟡",
    AgeKey.FROM_5_TO_7: "🟠",
    AgeKey.OVER_7: "🔴",
}


def age_key_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, title in AgeKey.choices:
        emoji = _AGE_EMOJI.get(key, "")
        text = f"{emoji} {title}".strip()
        builder.button(text=text, callback_data=AgeKeyCD(key=key).pack())
    builder.adjust(1)
    return builder.as_markup()


def format_age_key_title(key: str) -> str:
    title = dict(AgeKey.choices).get(key, key)
    emoji = _AGE_EMOJI.get(key, "")
    return f"{emoji} {title}".strip()


# HYBRID additions: fuel (ICE) selection and Yes/No switches
class HybridFuelCD(CallbackData, prefix="hf"):
    fuel: str  # "Бензин" | "Дизель"


def hybrid_fuel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    # Явно два варианта топлива ДВС в гибриде
    builder.button(text="🛢️ Бензин", callback_data=HybridFuelCD(fuel="Бензин").pack())
    builder.button(text="🛢️ Дизель", callback_data=HybridFuelCD(fuel="Дизель").pack())
    builder.adjust(1)
    return builder.as_markup()


class YesNoCD(CallbackData, prefix="yn"):
    val: str  # "yes" | "no"


def yes_no_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да", callback_data=YesNoCD(val="yes").pack())
    builder.button(text="❌ Нет", callback_data=YesNoCD(val="no").pack())
    builder.adjust(2)
    return builder.as_markup()


# POWER UNIT toggle (л.с. / кВт)
class PowerUnitCD(CallbackData, prefix="pu"):
    unit: str  # "hp" | "kw"


def power_unit_kb(selected: str = "hp", *, use_kw_30min: bool = False) -> InlineKeyboardMarkup:
    """Двухкнопочный переключатель единиц мощности.

    selected: "hp" (л.с.) или "kw" (кВт). Выбранная кнопка помечается ✅.
    use_kw_30min: если True, подпись для кВт будет «30‑минутная мощность, кВт»
      (официальная формулировка для ЭД по Правилам ЕЭК ООН №85 / ГОСТ Р 41.85).
    """
    selected = "kw" if str(selected).lower() == "kw" else "hp"
    hp_text = ("✅ л.с." if selected == "hp" else "л.с.")
    kw_label = "30‑минутная мощность, кВт" if use_kw_30min else "кВт"
    kw_text = (f"✅ {kw_label}" if selected == "kw" else kw_label)
    builder = InlineKeyboardBuilder()
    builder.button(text=hp_text, callback_data=PowerUnitCD(unit="hp").pack())
    builder.button(text=kw_text, callback_data=PowerUnitCD(unit="kw").pack())
    builder.adjust(2)
    return builder.as_markup()
