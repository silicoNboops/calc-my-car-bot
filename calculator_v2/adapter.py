# -*- coding: utf-8 -*-
"""
Адаптер для маппинга payload из бота (финальный шаг визарда)
в структуру VehicleSpec калькулятора v6 и запуска расчёта.

Не требует Django/ORM. Можно использовать напрямую из скриптов.
"""
from __future__ import annotations

from typing import Dict, Any

from . import (
    VehicleSpec,
    VehicleType,
    ImporterType,
    EngineType,
    FuelType,
    calculate_customs_payments,
)

# Значения из api/calculator/choices.py::AgeKey
_AGE_KEY_TO_YEARS: Dict[str, int] = {
    "under_3": 2,
    "3_to_5": 4,
    "5_to_7": 6,
    "over_7": 8,
    "over_5": 6,  # исторический ключ — принимаем как 5–7
}

# Значения из api/calculator/choices.py::EngineType (TextChoices, RU строки)
_ENGINE_TYPE_RU_TO_V6: Dict[str, EngineType] = {
    "Бензин": EngineType.DVS,
    "Дизель": EngineType.DVS,
    "Электро": EngineType.ELECTRIC,
    "Гибрид(послед)": EngineType.HYBRID_SERIES,
    "Гибрид(паралл)": EngineType.HYBRID_PARALLEL,
}

# Для пошлины у юрлиц важно топливо (дизель/бензин/электро/гибрид)
# В боте виден только тип двигателя. Маппим его к FuelType с разумными дефолтами.
_FUEL_BY_ENGINE_RU: Dict[str, FuelType] = {
    "Бензин": FuelType.GASOLINE,
    "Дизель": FuelType.DIESEL,
    "Электро": FuelType.ELECTRIC,
    # Для гибридов бота топливо ДВС не уточняется — считаем как бензо‑гибрид
    "Гибрид(послед)": FuelType.HYBRID,
    "Гибрид(паралл)": FuelType.HYBRID,
}

# Значения из api/calculator/choices.py::VehicleType уже совпадают со значениями v6
_VEHICLE_TYPE_FROM_STR: Dict[str, VehicleType] = {
    "car": VehicleType.CAR,
    "quad": VehicleType.QUAD,
    "snowmobile": VehicleType.SNOWMOBILE,
    "motorcycle": VehicleType.MOTORCYCLE,
}


def _derive_importer_type(is_jur: bool | None, is_personal_use: bool | None) -> ImporterType:
    if is_jur:
        return ImporterType.JURIDICAL
    # физлицо
    if is_personal_use is False:
        return ImporterType.PHYS_RESALE
    return ImporterType.PHYS_PERSONAL


def _map_engine_and_fuel(engine_type_ru: str | None) -> tuple[EngineType, FuelType]:
    et = _ENGINE_TYPE_RU_TO_V6.get(engine_type_ru or "", EngineType.DVS)
    fuel = _FUEL_BY_ENGINE_RU.get(engine_type_ru or "", FuelType.GASOLINE)
    return et, fuel


def _map_age_years(age_key: str | None) -> int:
    if not age_key:
        return 4
    return _AGE_KEY_TO_YEARS.get(age_key, 4)


def _map_vehicle_type(v: str | VehicleType | None) -> VehicleType:
    if isinstance(v, VehicleType):
        return v
    return _VEHICLE_TYPE_FROM_STR.get(str(v or "car"), VehicleType.CAR)


def map_bot_payload_to_v6_spec(payload: Dict[str, Any]) -> VehicleSpec:
    """Маппинг финального payload из визарда бота к VehicleSpec v6.

    Ожидаемый payload (из bot/routers/calculator.py::choose_age_key):
        {
            "price": float,
            "currency": str,  # "EUR"/"USD"/..., регистр не критичен
            "engine_cc": int,
            "hp": int,  # может быть 0 в текущей версии визарда
            "engine_type": str,  # RU: "Бензин"/"Дизель"/"Электро"/"Гибрид(послед)"/"Гибрид(паралл)"
            "age_key": str,  # "under_3" | "3_to_5" | "5_to_7" | "over_7" | "over_5"
            "is_jur": bool,
            "is_personal_use": bool | None,
            "vehicle_type": str,  # "car" | "quad" | "snowmobile" | "motorcycle"
        }
    """
    price = float(payload.get("price", 0.0))
    currency = str(payload.get("currency", "RUB"))
    engine_cc = int(payload.get("engine_cc", 0) or 0)
    power_hp = int(payload.get("hp", 0) or 0)

    engine_type_ru = payload.get("engine_type", None)
    engine_type, fuel_type = _map_engine_and_fuel(engine_type_ru)

    age_years = _map_age_years(str(payload.get("age_key", "3_to_5")))

    importer_type = _derive_importer_type(
        bool(payload.get("is_jur", False)),
        payload.get("is_personal_use", None),
    )

    vehicle_type = _map_vehicle_type(payload.get("vehicle_type"))

    # Для гибридов из бота уточняем только топологию. Предположим, что
    # последовательный гибрид трактуем как sequential; параллельный — parallel.
    is_series = engine_type == EngineType.HYBRID_SERIES

    # Нет данных о соотношении мощностей ДВС/ЭД. По-дефолту считаем ДВС сильнее,
    # чтобы не занижать акциз в коммерческих сценариях (консервативно).
    dvs_gt_electric = True

    return VehicleSpec(
        vehicle_type=vehicle_type,
        importer_type=importer_type,
        cost_original=price,
        currency=currency,
        age_years=age_years,
        engine_volume_cc=engine_cc,
        power_hp=power_hp,
        engine_type=engine_type,
        fuel_type=fuel_type,
        is_series_hybrid=is_series,
        dvs_power_greater_than_electric=dvs_gt_electric,
    )


def run_v6_with_bot_payload(payload: Dict[str, Any]):
    """Запускает расчёт v6 по payload бота и возвращает CalculationResult."""
    spec = map_bot_payload_to_v6_spec(payload)
    return calculate_customs_payments(spec)
