#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Таможенный калькулятор РФ v2.0 - Автомобили, Квадроциклы, Снегоходы
Дата: 17.08.2025

Поддерживает:
- Легковые автомобили (ДВС, электро, гибрид)
- Квадроциклы/мотовездеходы (ДВС, электро, гибрид)
- Снегоходы (ДВС, электро, гибрид)
- Физические и юридические лица
- Личное использование и коммерческое
- Актуальные ставки 2025 года

Основано на:
- НК РФ ст. 193 (акцизы)
- Постановление Правительства РФ № 1291
- Решения ЕЭК
- ФТС России
"""

import argparse
import logging
import sys

try:
    import requests  # Optional; tests can run without it
except ImportError:  # pragma: no cover
    requests = None
import datetime
from typing import Dict, Any
from dataclasses import dataclass
from enum import Enum

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class VehicleType(Enum):
    CAR = "car"
    QUAD = "quad"
    SNOWMOBILE = "snowmobile"
    MOTORCYCLE = "motorcycle"


class ImporterType(Enum):
    PHYS_PERSONAL = "phys_personal"
    PHYS_RESALE = "phys_resale"
    JURIDICAL = "juridical"


class EngineType(Enum):
    DVS = "dvs"  # ДВС (бензин/дизель)
    ELECTRIC = "electric"  # электро
    HYBRID_SERIES = "hybrid_series"  # последовательный гибрид
    HYBRID_PARALLEL = "hybrid_parallel"  # параллельный гибрид


class FuelType(Enum):
    GASOLINE = "gasoline"
    DIESEL = "diesel"
    ELECTRIC = "electric"
    HYBRID = "hybrid"
    DIESEL_ELECTRIC = "diesel_electric"  # дизельный и электрический
    GASOLINE_ELECTRIC = "gasoline_electric"  # бензиновый и электрический


@dataclass
class VehicleSpec:
    vehicle_type: VehicleType
    importer_type: ImporterType
    cost_original: float
    currency: str
    age_years: int
    engine_volume_cc: int  # 0 для электро
    power_hp: int
    engine_type: EngineType
    # Дополнительные параметры для гибридов
    dvs_power_hp: int = 0  # Мощность ДВС части для гибридов
    electric_power_hp: int = 0  # Мощность электро части для гибридов
    # Тип топлива/двигателя для ставок пошлины (юрлица)
    fuel_type: FuelType = FuelType.GASOLINE
    # Параметры для новых гибридных типов
    is_series_hybrid: bool = False  # Силовая установка последовательного типа
    dvs_power_greater_than_electric: bool = False  # Мощность ДВС больше максимальной 30-минутной мощности ЭД


@dataclass
class CalculationResult:
    cost_rub: float
    duty_rub: float
    excise_rub: float
    vat_rub: float
    util_fee_rub: float
    customs_fee_rub: float
    total_rub: float
    breakdown: Dict[str, Any]


# Курсы валют - интеграция с API ЦБ РФ

class RatesFetcher:
    """Класс для получения актуальных курсов валют с API ЦБ РФ"""
    CURRENCY_API_URL = "https://www.cbr-xml-daily.ru/daily_json.js"
    SUPPORTED = ["EUR", "USD", "CNY", "JPY", "KRW", "RUB"]

    # Кэш курсов для избежания частых запросов
    _cache = {}
    _cache_time = None
    _cache_duration = 3600  # 1 час в секундах

    @classmethod
    def get_currency_rates(cls) -> Dict[str, float]:
        """Получение актуальных курсов валют с кэшированием"""
        now = datetime.datetime.now()

        # Проверяем кэш
        if (cls._cache_time and
                (now - cls._cache_time).total_seconds() < cls._cache_duration and
                cls._cache):
            logger.info(f"Используются кэшированные курсы валют")
            return cls._cache

        try:
            if requests is None:
                raise RuntimeError("requests not available")
            logger.info("Получение актуальных курсов валют с API ЦБ РФ...")
            resp = requests.get(cls.CURRENCY_API_URL, timeout=10)
            resp.raise_for_status()
            j = resp.json()

            rates = {"RUB": 1.0}
            for code in cls.SUPPORTED:
                if code == "RUB":
                    continue
                if code in j["Valute"]:
                    val = j["Valute"][code]["Value"]
                    nominal = j["Valute"][code]["Nominal"]
                    rates[code] = float(val) / float(nominal)

            # Обновляем кэш
            cls._cache = rates
            cls._cache_time = now

            logger.info(f"Курсы валют обновлены: EUR={rates.get('EUR', 0):.4f}, USD={rates.get('USD', 0):.4f}")
            return rates

        except Exception as e:
            logger.warning(f"Не удалось получить курсы ЦБ РФ: {e}. Использую fallback.")
            # Fallback курсы
            fallback_rates = {
                "EUR": 100.0, "USD": 90.0, "CNY": 13.5,
                "JPY": 0.65, "KRW": 0.07, "RUB": 1.0
            }
            cls._cache = fallback_rates
            cls._cache_time = now
            return fallback_rates


def get_exchange_rate(currency: str) -> float:
    """Получение курса конкретной валюты к рублю"""
    rates = RatesFetcher.get_currency_rates()
    return rates.get(currency.upper(), 1.0)


# Константы ставок 2025 года
RATES_2025 = {
    # Акцизные ставки (руб/л.с. или руб/кВт) - НК РФ ст. 193
    'EXCISE_RATES': [
        {'max_hp': 90, 'rate': 0},
        {'max_hp': 150, 'rate': 61},
        {'max_hp': 200, 'rate': 583},
        {'max_hp': 300, 'rate': 955},
        {'max_hp': 400, 'rate': 1628},
        {'max_hp': 500, 'rate': 1685},
        {'max_hp': float('inf'), 'rate': 1740}
    ],

    # Утилизационный сбор - базовые ставки
    'UTIL_BASE': {
        'car': 20000,
        'quad': 172500,
        'snowmobile': 172500,
        'motorcycle': 172500  # как для квадроциклов
    },

    # Коэффициенты утилизационного сбора
    'UTIL_COEFFS': {
        # Для физлиц личное использование
        'personal': {
            'car': {'new': 3400, 'old': 5200},  # фиксированные суммы
            'quad': {'new': 1.63, 'old': 6.1},
            'snowmobile': {'new': 1.63, 'old': 6.1},
            'motorcycle': {'new': 1.63, 'old': 6.1}
        },
        # Для коммерческого использования (физлица для перепродажи + юрлица)
        'commercial': {
            'car': {
                # Коэффициенты по объему двигателя для ДВС
                'new_dvs_by_volume': [
                    {'max_cc': 1000, 'coeff': 9.01},  # 180,200 / 20,000 = 9.01
                    {'max_cc': 2000, 'coeff': 33.37},  # 667,400 / 20,000 = 33.37
                    {'max_cc': 3000, 'coeff': 93.77},  # 1,875,400 / 20,000 = 93.77
                    {'max_cc': 3500, 'coeff': 107.67},  # 2,153,400 / 20,000 = 107.67
                    {'max_cc': float('inf'), 'coeff': 137.11}  # 2,742,200 / 20,000 = 137.11
                ],
                'old_dvs_by_volume': [
                    {'max_cc': 1000, 'coeff': 23.0},  # 460,000 / 20,000 = 23.0
                    {'max_cc': 2000, 'coeff': 58.7},  # 1,174,000 / 20,000 = 58.7
                    {'max_cc': 3000, 'coeff': 141.97},  # 2,839,400 / 20,000 = 141.97
                    {'max_cc': 3500, 'coeff': 164.84},  # 3,296,800 / 20,000 = 164.84
                    {'max_cc': float('inf'), 'coeff': 180.24}  # 3,604,800 / 20,000 = 180.24
                ],
                'new_electric': 33.37, 'old_electric': 58.7,  # 667,400 / 20,000 = 33.37, 1,174,000 / 20,000 = 58.7
                'new_hybrid': 33.37, 'old_hybrid': 58.7  # Как для электромобилей
            },
            'quad': {'new': 1.63, 'old': 6.1},
            'snowmobile': {'new': 1.63, 'old': 6.1},
            'motorcycle': {'new': 1.63, 'old': 6.1}
        }
    },

    # Пошлины для автомобилей по правилам rules_poshlina.txt
    'CAR_DUTY': {
        'personal_ets': {
            # Физлица (личное и перепродажа)
            'under_3': [
                {'max_value_eur': 8500, 'rate': 0.54, 'min_eur_cc': 2.5},
                {'max_value_eur': 16700, 'rate': 0.48, 'min_eur_cc': 3.5},
                {'max_value_eur': 42300, 'rate': 0.48, 'min_eur_cc': 5.5},
                {'max_value_eur': 84500, 'rate': 0.48, 'min_eur_cc': 7.5},
                {'max_value_eur': 169000, 'rate': 0.48, 'min_eur_cc': 15.0},
                {'max_value_eur': float('inf'), 'rate': 0.48, 'min_eur_cc': 20.0}
            ],
            # 3-5 лет
            'between_3_5': [
                {'max_cc': 1000, 'rate_eur_cc': 1.5},
                {'max_cc': 1500, 'rate_eur_cc': 1.7},
                {'max_cc': 1800, 'rate_eur_cc': 2.5},
                {'max_cc': 2300, 'rate_eur_cc': 2.7},
                {'max_cc': 3000, 'rate_eur_cc': 3.0},
                {'max_cc': float('inf'), 'rate_eur_cc': 3.6}
            ],
            # Старше 5 лет
            'over_5': [
                {'max_cc': 1000, 'rate_eur_cc': 3.0},
                {'max_cc': 1500, 'rate_eur_cc': 3.2},
                {'max_cc': 1800, 'rate_eur_cc': 3.5},
                {'max_cc': 2300, 'rate_eur_cc': 4.8},
                {'max_cc': 3000, 'rate_eur_cc': 5.0},
                {'max_cc': float('inf'), 'rate_eur_cc': 5.7}
            ]
        },
        # Юрлица
        'juridical': {
            'under_3': {
                'gasoline_or_hybrid': [
                    {'max_cc': 1000, 'rate': 0.15},
                    {'max_cc': 1500, 'rate': 0.15},
                    {'max_cc': 1800, 'rate': 0.15},
                    {'max_cc': 2300, 'rate': 0.15},
                    {'max_cc': 2800, 'rate': 0.15},
                    {'max_cc': 3000, 'rate': 0.125},
                    {'max_cc': float('inf'), 'rate': 0.125}
                ],
                'diesel_rate': 0.15
            },
            'between_3_7': {
                'gasoline_or_hybrid_min_eur_cc': [
                    {'max_cc': 1000, 'min_eur_cc': 0.36},
                    {'max_cc': 1500, 'min_eur_cc': 0.40},
                    {'max_cc': 1800, 'min_eur_cc': 0.36},
                    {'max_cc': 2300, 'min_eur_cc': 0.44},
                    {'max_cc': 2800, 'min_eur_cc': 0.44},
                    {'max_cc': 3000, 'min_eur_cc': 0.44},
                    {'max_cc': float('inf'), 'min_eur_cc': 0.80}
                ],
                'diesel_min_eur_cc': [
                    {'max_cc': 1500, 'min_eur_cc': 0.32},
                    {'max_cc': 2500, 'min_eur_cc': 0.40},
                    {'max_cc': float('inf'), 'min_eur_cc': 0.80}
                ],
                'percent_rate': 0.20
            },
            'over_7': {
                'gasoline_or_hybrid_eur_cc': [
                    {'max_cc': 1000, 'eur_cc': 1.4},
                    {'max_cc': 1500, 'eur_cc': 1.5},
                    {'max_cc': 1800, 'eur_cc': 1.6},
                    {'max_cc': 2300, 'eur_cc': 2.2},
                    {'max_cc': 2800, 'eur_cc': 2.2},
                    {'max_cc': 3000, 'eur_cc': 2.2},
                    {'max_cc': float('inf'), 'eur_cc': 3.2}
                ],
                'diesel_eur_cc': [
                    {'max_cc': 1500, 'eur_cc': 1.5},
                    {'max_cc': 2500, 'eur_cc': 2.2},
                    {'max_cc': float('inf'), 'eur_cc': 3.2}
                ]
            }
        }
    },
    # ЗАГОТОВКА: таблицы ЕТТ для юрлиц (по ТН ВЭД 8703, диап. объема)
    # TODO: заполнить по официальным ставкам ЕТТ ЕАЭС (Решения ЕЭК)
    'CAR_DUTY_ETT': {
        'gasoline': {
            'new': [
                # {'max_cc': 1000, 'rate': 0.15, 'min_eur_cc': 0.XX},
            ],
            'old': [
            ]
        },
        'diesel': {
            'new': [],
            'old': []
        },
        'hybrid': {
            'new': [],
            'old': []
        },
        'electric': {
            'new': [],
            'old': []
        }
    },

    # Пошлины для мотоциклов по rules_poshlina.txt
    'MOTORCYCLE_DUTY': {
        'phys_under_3': [
            {'max_cc': 125, 'rate': 0.10, 'min_eur_cc': 0.8},
            {'max_cc': 500, 'rate': 0.15, 'min_eur_cc': 1.0},
            {'max_cc': 800, 'rate': 0.20, 'min_eur_cc': 1.2},
            {'max_cc': float('inf'), 'rate': 0.20, 'min_eur_cc': 1.5}
        ],
        'phys_over_3': [
            {'max_cc': 125, 'eur_cc': 0.8},
            {'max_cc': 500, 'eur_cc': 1.0},
            {'max_cc': 800, 'eur_cc': 1.2},
            {'max_cc': float('inf'), 'eur_cc': 1.5}
        ],
        'jur_under_3_rate': 0.06,
        'jur_over_3': [
            {'max_cc': 125, 'rate': 0.10, 'min_eur_cc': 0.10},
            {'max_cc': 500, 'rate': 0.10, 'min_eur_cc': 0.15},
            {'max_cc': 800, 'rate': 0.10, 'min_eur_cc': 0.20},
            {'max_cc': float('inf'), 'rate': 0.10, 'min_eur_cc': 0.25}
        ]
    },

    # Пошлины для квадроциклов (ATV) по rules_poshlina.txt
    'QUAD_DUTY': {
        'phys_under_3': {
            'rate': 0.25,
            'min_eur_hp': {'le_50': 1.0, 'gt_50': 2.0}
        },
        'phys_over_3': {
            'eur_hp': {'le_50': 1.0, 'gt_50': 2.0}
        },
        'jur_under_3_rate': 0.15,
        'jur_over_3': {
            'rate': 0.20,
            'min_eur_hp': 0.5
        }
    },

    # Пошлины для снегоходов по rules_poshlina.txt
    'SNOWMOBILE_DUTY': {
        'phys_under_3': {
            'rate': 0.15,
            'min_eur_hp': {'le_100': 1.5, 'gt_100': 3.0}
        },
        'phys_over_3': {
            'eur_hp': {'le_100': 1.5, 'gt_100': 3.0}
        },
        'jur_under_3_rate': 0.10,
        'jur_over_3': {
            'rate': 0.15,
            'min_eur_hp': 1.0
        }
    },

    # НДС
    'VAT_RATE': 0.20,

    # Таможенные сборы (руб) — официальные ставки с 01.01.2025 (ПП РФ № 1637)
    'CUSTOMS_FEES': [
        {'max_value_rub': 200000, 'fee': 1067},
        {'max_value_rub': 450000, 'fee': 2134},
        {'max_value_rub': 1200000, 'fee': 4269},
        {'max_value_rub': 2700000, 'fee': 11746},
        {'max_value_rub': 4200000, 'fee': 16524},
        {'max_value_rub': 5500000, 'fee': 21344},
        {'max_value_rub': 7000000, 'fee': 27540},
        {'max_value_rub': float('inf'), 'fee': 30000}
    ]
}


def find_rate_by_value(value: float, rates_table: list, key: str) -> dict:
    """Поиск ставки по значению в таблице"""
    for rate in rates_table:
        if value <= rate.get(key, float('inf')):
            return rate
    return rates_table[-1]


def calc_excise_progressive(power_hp: int) -> float:
    """Прогрессивный расчет акциза по диапазонам мощности (НК РФ ст. 193)"""
    if power_hp <= 90:
        return 0.0

    excise = 0.0

    # Диапазон 91-150 л.с.: 61 руб/л.с.
    if power_hp > 90:
        power_in_range = min(power_hp, 150) - 90
        excise += power_in_range * 61
        if power_hp <= 150:
            return excise

    # Диапазон 151-200 л.с.: 583 руб/л.с.
    if power_hp > 150:
        power_in_range = min(power_hp, 200) - 150
        excise += power_in_range * 583
        if power_hp <= 200:
            return excise

    # Диапазон 201-300 л.с.: 955 руб/л.с.
    if power_hp > 200:
        power_in_range = min(power_hp, 300) - 200
        excise += power_in_range * 955
        if power_hp <= 300:
            return excise

    # Диапазон 301-400 л.с.: 1628 руб/л.с.
    if power_hp > 300:
        power_in_range = min(power_hp, 400) - 300
        excise += power_in_range * 1628
        if power_hp <= 400:
            return excise

    # Диапазон 401-500 л.с.: 1685 руб/л.с.
    if power_hp > 400:
        power_in_range = min(power_hp, 500) - 400
        excise += power_in_range * 1685
        if power_hp <= 500:
            return excise

    # Диапазон свыше 500 л.с.: 1740 руб/л.с.
    if power_hp > 500:
        power_in_range = power_hp - 500
        excise += power_in_range * 1740

    return excise


def calc_excise_electric(power_hp: int) -> float:
    """Расчет акциза для электромобилей по диапазонам мощности согласно electro_car_rules.txt
    
    Ставки акциза на электромобили (2025):
    - до 90 л.с. включительно: 0 рублей
    - свыше 90 и до 150 л.с.: 61 рубль за 1 л.с.
    - свыше 150 и до 200 л.с.: 583 рубля за 1 л.с.
    - свыше 200 до 300 л.с.: 955 рублей за 1 л.с.
    - свыше 300 и до 400 л.с.: 1628 рублей за 1 л.с.
    - свыше 400 и до 500 л.с.: 1685 рублей за 1 л.с.
    - свыше 500 л.с.: 1740 рублей за 1 л.с.
    """
    if power_hp <= 90:
        return 0.0
    elif power_hp <= 150:
        return float(power_hp) * 61.0
    elif power_hp <= 200:
        return float(power_hp) * 583.0
    elif power_hp <= 300:
        return float(power_hp) * 955.0
    elif power_hp <= 400:
        return float(power_hp) * 1628.0
    elif power_hp <= 500:
        return float(power_hp) * 1685.0
    else:
        return float(power_hp) * 1740.0


def calc_excise_flat(power_hp: int) -> float:
    """Расчет акциза по диапазонам: ставка применяется ко ВСЕЙ мощности"""
    if power_hp <= 90:
        return 0.0
    # Найти подходящую ставку по таблице RATES_2025['EXCISE_RATES']
    for bracket in RATES_2025['EXCISE_RATES']:
        if power_hp <= bracket['max_hp']:
            return float(power_hp) * float(bracket['rate'])
    # На всякий случай (хотя последняя граница inf)
    last = RATES_2025['EXCISE_RATES'][-1]
    return float(power_hp) * float(last['rate'])


def calc_excise(spec: VehicleSpec) -> float:
    """Расчет акциза с учетом типа двигателя и ставок
    
    Физические лица, покупающие автомобили для личного использования,
    освобождаются от уплаты акциза.
    Однако электромобили облагаются акцизом даже для физлиц личное использование.
    
    Новая логика для гибридов:
    - Последовательный гибрид, ЭД ≥ ДВС → считаем как электромобиль (акциз по ЭД)
    - Последовательный гибрид, ДВС > ЭД → считаем как ДВС (акциз по ДВС)
    - Параллельный гибрид → считаем как ДВС (акциз по ДВС)
    """
    # Акциз применяется для легковых автомобилей и мотоциклов
    if spec.vehicle_type == VehicleType.MOTORCYCLE:
        # Для мотоциклов: акциз только если мощность > 150 л.с.
        if spec.power_hp > 150:
            return spec.power_hp * 583.0
        else:
            return 0.0

    # Для квадроциклов/снегоходов акциз не применяется
    if spec.vehicle_type not in [VehicleType.CAR, VehicleType.MOTORCYCLE]:
        return 0.0

    # Обработка электромобилей
    if spec.engine_type == EngineType.ELECTRIC or spec.fuel_type == FuelType.ELECTRIC:
        # Электромобили облагаются акцизом даже для физлиц личное использование
        # Согласно electro_car_rules.txt
        return calc_excise_electric(spec.power_hp)

    # Обработка новых гибридных типов
    if spec.fuel_type in [FuelType.DIESEL_ELECTRIC, FuelType.GASOLINE_ELECTRIC]:
        if spec.is_series_hybrid:
            # Последовательный гибрид
            if spec.dvs_power_greater_than_electric:
                # ДВС > ЭД → считаем как ДВС
                # Физические лица освобождены от акциза на ДВС
                if spec.importer_type in (ImporterType.PHYS_PERSONAL, ImporterType.PHYS_RESALE):
                    return 0.0
                return calc_excise_flat(spec.power_hp)
            else:
                # ЭД ≥ ДВС → считаем как электромобиль
                return calc_excise_electric(spec.power_hp)
        else:
            # Параллельный гибрид → считаем как ДВС
            # Физические лица освобождены от акциза на ДВС
            if spec.importer_type in (ImporterType.PHYS_PERSONAL, ImporterType.PHYS_RESALE):
                return 0.0
            return calc_excise_flat(spec.power_hp)

    # Физические лица (личное использование и перепродажа) освобождены от акциза на обычные автомобили (не электро)
    if spec.vehicle_type == VehicleType.CAR and spec.importer_type in (ImporterType.PHYS_PERSONAL,
                                                                       ImporterType.PHYS_RESALE):
        return 0.0

    if spec.engine_type == EngineType.HYBRID_SERIES:
        # Последовательный гибрид — используем общую мощность
        return calc_excise_flat(spec.power_hp)

    elif spec.engine_type == EngineType.HYBRID_PARALLEL:
        # Параллельный гибрид — используем общую мощность
        return calc_excise_flat(spec.power_hp)

    else:
        # Для ДВС — расчет по диапазонам мощности (НК РФ ст. 193)
        return calc_excise_flat(spec.power_hp)


def calc_util_fee(vehicle_type: VehicleType, importer_type: ImporterType,
                  age_years: int, engine_type: EngineType, engine_volume_cc: int,
                  spec: VehicleSpec = None) -> float:
    """Расчет утилизационного сбора"""
    # Для мотоциклов утилизационный сбор не платится
    if vehicle_type == VehicleType.MOTORCYCLE:
        return 0.0

    vehicle_key = vehicle_type.value
    is_new = age_years <= 3
    age_key = 'new' if is_new else 'old'

    base_rate = RATES_2025['UTIL_BASE'][vehicle_key]

    # Специальная логика для квадроциклов согласно quad_rules.txt
    if vehicle_key == 'quad':
        # Базовая ставка: 172 500 руб.
        base_rate = 172500

        # Для физических лиц (личное использование) применяем правила K01/K02
        if importer_type == ImporterType.PHYS_PERSONAL:
            # Для электрических квадроциклов применяем K01 (как для объема < 300 см³)
            if engine_type == EngineType.ELECTRIC:
                # K01: электро квадроциклы
                if is_new:
                    return base_rate * 0.4  # 69 000 руб.
                else:
                    return base_rate * 0.7  # 120 750 руб.
            elif engine_volume_cc < 300:
                # K01: объем < 300 см³
                if is_new:
                    return base_rate * 0.4  # 69 000 руб.
                else:
                    return base_rate * 0.7  # 120 750 руб.
            else:
                # K02: объем ≥ 300 см³
                if is_new:
                    return base_rate * 0.7  # 120 750 руб.
                else:
                    return base_rate * 1.3  # 224 250 руб.

        # Для юридических лиц и физлиц-перепродажа:
        # Согласно официальным данным, применяется коэффициент в зависимости от объема и возраста
        else:
            # Для электрических квадроциклов юрлиц применяется логика K02 (как для объема ≥ 300 см³)
            if engine_type == EngineType.ELECTRIC:
                # Для старых электрических квадроциклов юрлиц применяется K02
                if is_new:
                    return base_rate * 0.7  # 120 750 руб.
                else:
                    return base_rate * 1.3  # 224 250 руб.
            # Для бензиновых квадроциклов юрлиц применяется логика K01/K02
            elif engine_volume_cc < 300:
                # K01: объем < 300 см³
                if is_new:
                    return base_rate * 0.4  # 69 000 руб.
                else:
                    return base_rate * 0.7  # 120 750 руб.
            else:
                # K02: объем ≥ 300 см³
                if is_new:
                    return base_rate * 0.7  # 120 750 руб.
                else:
                    return base_rate * 1.3  # 224 250 руб.

    # Специальная логика для снегоходов согласно snowmobile_rules.txt
    if vehicle_key == 'snowmobile':
        # Базовая ставка: 172 500 руб.
        base_rate = 172500

        # Для физических лиц (личное использование) применяем правила L01/L02
        if importer_type == ImporterType.PHYS_PERSONAL:
            # Для электрических снегоходов применяем L01 (как для объема < 300 см³)
            if engine_type == EngineType.ELECTRIC:
                # L01: электро снегоходы
                if is_new:
                    return base_rate * 0.4  # 69 000 руб.
                else:
                    return base_rate * 0.7  # 120 750 руб.
            elif engine_volume_cc < 300:
                # L01: объем < 300 см³
                if is_new:
                    return base_rate * 0.4  # 69 000 руб.
                else:
                    return base_rate * 0.7  # 120 750 руб.
            else:
                # L02: объем ≥ 300 см³
                if is_new:
                    return base_rate * 0.7  # 120 750 руб.
                else:
                    return base_rate * 1.3  # 224 250 руб.

        # Для юридических лиц и физлиц-перепродажа:
        # Согласно официальным данным, применяется аналогичная логика
        else:
            # Для электрических снегоходов юрлиц применяется логика как для L02 (объем ≥ 300 см³)
            if engine_type == EngineType.ELECTRIC:
                if is_new:
                    return base_rate * 0.7  # 120 750 руб.
                else:
                    return base_rate * 1.3  # 224 250 руб.
            # Для бензиновых снегоходов юрлиц применяется логика L01/L02
            elif engine_volume_cc < 300:
                # L01: объем < 300 см³
                if is_new:
                    return base_rate * 0.4  # 69 000 руб.
                else:
                    return base_rate * 0.7  # 120 750 руб.
            else:
                # L02: объем ≥ 300 см³
                if is_new:
                    return base_rate * 0.7  # 120 750 руб.
                else:
                    return base_rate * 1.3  # 224 250 руб.

    if importer_type == ImporterType.PHYS_PERSONAL:
        # Для физлиц личное использование - фиксированные суммы
        if vehicle_key == 'car':
            return RATES_2025['UTIL_COEFFS']['personal'][vehicle_key][age_key]
        else:
            coeff = RATES_2025['UTIL_COEFFS']['personal'][vehicle_key][age_key]
            return base_rate * coeff
    else:
        # Для физлиц на перепродажу и юрлиц используем коммерческие коэффициенты
        if vehicle_key == 'car':
            # Новая логика для гибридных типов
            if spec and spec.fuel_type in [FuelType.DIESEL_ELECTRIC, FuelType.GASOLINE_ELECTRIC]:
                if spec.is_series_hybrid:
                    # Последовательный гибрид
                    if spec.dvs_power_greater_than_electric:
                        # ДВС > ЭД → считаем как ДВС (утилизационный сбор по объему ДВС)
                        volume_table = RATES_2025['UTIL_COEFFS']['commercial'][vehicle_key][f"{age_key}_dvs_by_volume"]
                        rate_info = find_rate_by_value(engine_volume_cc, volume_table, 'max_cc')
                        coeff = rate_info['coeff']
                    else:
                        # ЭД ≥ ДВС → считаем как электромобиль (утилизационный сбор 3400/5200)
                        coeff = RATES_2025['UTIL_COEFFS']['commercial'][vehicle_key][f"{age_key}_electric"]
                else:
                    # Параллельный гибрид → считаем как ДВС (утилизационный сбор по объему ДВС)
                    volume_table = RATES_2025['UTIL_COEFFS']['commercial'][vehicle_key][f"{age_key}_dvs_by_volume"]
                    rate_info = find_rate_by_value(engine_volume_cc, volume_table, 'max_cc')
                    coeff = rate_info['coeff']
            elif engine_type == EngineType.ELECTRIC:
                coeff = RATES_2025['UTIL_COEFFS']['commercial'][vehicle_key][f"{age_key}_electric"]
            elif engine_type in [EngineType.HYBRID_SERIES, EngineType.HYBRID_PARALLEL]:
                coeff = RATES_2025['UTIL_COEFFS']['commercial'][vehicle_key][f"{age_key}_hybrid"]
            else:
                # ДВС - коэффициент по объему двигателя
                volume_table = RATES_2025['UTIL_COEFFS']['commercial'][vehicle_key][f"{age_key}_dvs_by_volume"]
                rate_info = find_rate_by_value(engine_volume_cc, volume_table, 'max_cc')
                coeff = rate_info['coeff']
        else:
            coeff = RATES_2025['UTIL_COEFFS']['commercial'][vehicle_key][age_key]

        return base_rate * coeff


def calc_customs_fee(cost_rub: float, importer_type: ImporterType) -> float:
    """Расчет таможенного сбора по таблице ПП РФ № 1637 (единые ставки для всех импортёров).

    Согласно справочнику tamoj_sbor.txt: сбор рассчитывается по шкале в зависимости
    от таможенной стоимости и применяется одинаково для физлиц и юрлиц.
    База расчета — таможенная стоимость (без учета пошлины/НДС/акциза).
    """
    rate_info = find_rate_by_value(cost_rub, RATES_2025['CUSTOMS_FEES'], 'max_value_rub')
    return rate_info['fee']


def calc_car_duty(spec: VehicleSpec, cost_eur: float) -> float:
    """Расчет пошлины для автомобилей по rules_poshlina.txt."""
    # Электромобили: фиксировано 15% от стоимости для всех категорий
    if spec.engine_type == EngineType.ELECTRIC or spec.fuel_type == FuelType.ELECTRIC:
        return cost_eur * 0.15

    # Новая логика для гибридов
    if spec.fuel_type in [FuelType.DIESEL_ELECTRIC, FuelType.GASOLINE_ELECTRIC]:
        if spec.is_series_hybrid:
            # Последовательный гибрид
            if spec.dvs_power_greater_than_electric:
                # ДВС > ЭД → считаем как ДВС (пошлина по объему ДВС)
                pass  # продолжаем обычную логику ниже
            else:
                # ЭД ≥ ДВС → считаем как электромобиль (пошлина 15%)
                return cost_eur * 0.15
        # Параллельный гибрид → считаем как ДВС (пошлина по объему ДВС)

    # Физлица (личное и перепродажа) — ЕТС
    if spec.importer_type in (ImporterType.PHYS_PERSONAL, ImporterType.PHYS_RESALE):
        if spec.age_years < 3:
            rate_info = find_rate_by_value(cost_eur,
                                           RATES_2025['CAR_DUTY']['personal_ets']['under_3'],
                                           'max_value_eur')
            duty_by_value = cost_eur * rate_info['rate']
            duty_by_volume = spec.engine_volume_cc * rate_info['min_eur_cc']
            return max(duty_by_value, duty_by_volume)
        elif 3 <= spec.age_years <= 5:
            table = RATES_2025['CAR_DUTY']['personal_ets']['between_3_5']
            rate_info = find_rate_by_value(spec.engine_volume_cc, table, 'max_cc')
            return spec.engine_volume_cc * rate_info['rate_eur_cc']
        else:  # >5 лет
            table = RATES_2025['CAR_DUTY']['personal_ets']['over_5']
            rate_info = find_rate_by_value(spec.engine_volume_cc, table, 'max_cc')
            return spec.engine_volume_cc * rate_info['rate_eur_cc']

    # Юрлица
    # Определяем тип топлива для расчета пошлины
    is_diesel = (spec.fuel_type in [FuelType.DIESEL, FuelType.DIESEL_ELECTRIC])

    if spec.age_years < 3:
        if is_diesel:
            rate = RATES_2025['CAR_DUTY']['juridical']['under_3']['diesel_rate']
            return cost_eur * rate
        table = RATES_2025['CAR_DUTY']['juridical']['under_3']['gasoline_or_hybrid']
        rate_info = find_rate_by_value(spec.engine_volume_cc, table, 'max_cc')
        return cost_eur * rate_info['rate']

    elif 3 <= spec.age_years <= 7:
        percent = RATES_2025['CAR_DUTY']['juridical']['between_3_7']['percent_rate']
        if is_diesel:
            table = RATES_2025['CAR_DUTY']['juridical']['between_3_7']['diesel_min_eur_cc']
            min_info = find_rate_by_value(spec.engine_volume_cc, table, 'max_cc')
            duty_by_value = cost_eur * percent
            duty_by_volume = spec.engine_volume_cc * min_info['min_eur_cc']
            return max(duty_by_value, duty_by_volume)
        else:  # бензин/гибрид
            table = RATES_2025['CAR_DUTY']['juridical']['between_3_7']['gasoline_or_hybrid_min_eur_cc']
            min_info = find_rate_by_value(spec.engine_volume_cc, table, 'max_cc')
            duty_by_value = cost_eur * percent
            duty_by_volume = spec.engine_volume_cc * min_info['min_eur_cc']
            return max(duty_by_value, duty_by_volume)

    else:  # >7 лет
        if is_diesel:
            table = RATES_2025['CAR_DUTY']['juridical']['over_7']['diesel_eur_cc']
            info = find_rate_by_value(spec.engine_volume_cc, table, 'max_cc')
            return spec.engine_volume_cc * info['eur_cc']
        else:
            table = RATES_2025['CAR_DUTY']['juridical']['over_7']['gasoline_or_hybrid_eur_cc']
            info = find_rate_by_value(spec.engine_volume_cc, table, 'max_cc')
            return spec.engine_volume_cc * info['eur_cc']


def calc_quad_duty(spec: VehicleSpec, cost_eur: float) -> float:
    """Расчет пошлины для квадроциклов по quad_rules.txt
    
    Для юридических лиц:
    - Новые (≤ 3 лет): 15% для электро, 5% для ДВС
    - Старые (4-7 лет): 20%, но не менее 0.36 евро/см³ для ДВС
    - Очень старые (> 7 лет): фиксированная ставка 1.4 евро/см³
    """
    # Для электрических квадроциклов применяем ставку 15%
    if spec.engine_type == EngineType.ELECTRIC:
        return cost_eur * 0.15

    # Для юридических лиц с ДВС квадроциклами
    if spec.importer_type == ImporterType.JURIDICAL:
        if spec.age_years <= 3:
            # Новые квадроциклы: 5%
            return cost_eur * 0.05
        elif spec.age_years <= 7:
            # Старые квадроциклы (4-7 лет): 20%, но не менее 0.36 евро/см³
            duty_by_percent = cost_eur * 0.20
            duty_by_volume = spec.engine_volume_cc * 0.36
            return max(duty_by_percent, duty_by_volume)
        else:
            # Очень старые квадроциклы (> 7 лет): фиксированная ставка 1.4 евро/см³
            return spec.engine_volume_cc * 1.4

    # Для физлиц: по умолчанию 5% (можно доработать по более сложным правилам)
    return cost_eur * 0.05


def calc_snowmobile_duty(spec: VehicleSpec, cost_eur: float) -> float:
    """Расчет пошлины для снегоходов
    
    Все снегоходы используют 5% пошлину независимо от возраста
    """
    return cost_eur * 0.05


def calc_motorcycle_duty(spec: VehicleSpec, cost_eur: float) -> float:
    """Расчет пошлины для мотоциклов по moto_akciz.txt
    
    Пошлины одинаковые для всех (физлица, юрлица, ИП) и не зависят от возраста.
    Ставки зависят только от объема двигателя.
    """
    # Электрические мотоциклы
    if spec.engine_type == EngineType.ELECTRIC:
        return cost_eur * 0.15

    # ДВС мотоциклы по объему двигателя
    volume_cc = spec.engine_volume_cc

    if volume_cc <= 50:
        return cost_eur * 0.14
    elif volume_cc <= 125:
        return cost_eur * 0.14
    elif volume_cc <= 250:
        return cost_eur * 0.14
    elif volume_cc <= 380:
        return cost_eur * 0.15
    elif volume_cc <= 500:
        return cost_eur * 0.15
    elif volume_cc <= 800:
        return cost_eur * 0.15
    else:  # > 800 см³
        return cost_eur * 0.10


def calculate_customs_payments(spec: VehicleSpec) -> CalculationResult:
    """Основная функция расчета таможенных платежей"""

    # Конвертация в рубли
    exchange_rate = get_exchange_rate(spec.currency)
    cost_rub = spec.cost_original * exchange_rate

    # Конвертация в евро для расчета пошлин
    eur_rate = get_exchange_rate('EUR')
    cost_eur = cost_rub / eur_rate

    # Расчет пошлины в зависимости от типа ТС
    if spec.vehicle_type == VehicleType.CAR:
        duty_eur = calc_car_duty(spec, cost_eur)
    elif spec.vehicle_type == VehicleType.QUAD:
        duty_eur = calc_quad_duty(spec, cost_eur)
    elif spec.vehicle_type == VehicleType.MOTORCYCLE:
        duty_eur = calc_motorcycle_duty(spec, cost_eur)
    else:  # SNOWMOBILE
        duty_eur = calc_snowmobile_duty(spec, cost_eur)

    duty_rub = duty_eur * eur_rate

    # Акциз (для легковых автомобилей и мотоциклов - НК РФ ст. 193)
    excise_rub = 0.0
    if spec.vehicle_type in [VehicleType.CAR, VehicleType.MOTORCYCLE]:
        excise_rub = calc_excise(spec)

    # НДС (для юридических лиц и электромобилей для всех)
    vat_rub = 0.0
    is_electric_for_vat = (spec.engine_type == EngineType.ELECTRIC or
                           spec.fuel_type == FuelType.ELECTRIC or
                           (spec.fuel_type in [FuelType.DIESEL_ELECTRIC, FuelType.GASOLINE_ELECTRIC] and
                            spec.is_series_hybrid and not spec.dvs_power_greater_than_electric))

    if (spec.importer_type == ImporterType.JURIDICAL or
            (is_electric_for_vat and spec.vehicle_type == VehicleType.CAR)):
        vat_base = cost_rub + duty_rub + excise_rub
        vat_rub = vat_base * RATES_2025['VAT_RATE']

    # Утилизационный сбор
    util_fee_rub = calc_util_fee(spec.vehicle_type, spec.importer_type,
                                 spec.age_years, spec.engine_type, spec.engine_volume_cc, spec)

    # Таможенный сбор
    customs_fee_rub = calc_customs_fee(cost_rub, spec.importer_type)

    # Итого
    total_rub = duty_rub + excise_rub + vat_rub + util_fee_rub + customs_fee_rub

    # Детализация для отчета
    breakdown = {
        'cost_original': spec.cost_original,
        'currency': spec.currency,
        'exchange_rate': exchange_rate,
        'cost_eur': cost_eur,
        'duty_eur': duty_eur,
        'eur_rate': eur_rate,
        'vehicle_type_ru': {
            VehicleType.CAR: 'Легковой автомобиль',
            VehicleType.QUAD: 'Квадроцикл',
            VehicleType.SNOWMOBILE: 'Снегоход',
            VehicleType.MOTORCYCLE: 'Мотоцикл'
        }[spec.vehicle_type],
        'importer_type_ru': {
            ImporterType.PHYS_PERSONAL: 'Физлицо (личное использование)',
            ImporterType.PHYS_RESALE: 'Физлицо (перепродажа)',
            ImporterType.JURIDICAL: 'Юридическое лицо'
        }[spec.importer_type],
        'engine_type_ru': get_engine_type_description(spec)
    }

    return CalculationResult(
        cost_rub=cost_rub,
        duty_rub=duty_rub,
        excise_rub=excise_rub,
        vat_rub=vat_rub,
        util_fee_rub=util_fee_rub,
        customs_fee_rub=customs_fee_rub,
        total_rub=total_rub,
        breakdown=breakdown
    )


def get_engine_type_description(spec: VehicleSpec) -> str:
    """Получение описания типа двигателя"""
    if spec.fuel_type == FuelType.ELECTRIC:
        return 'Электро'
    elif spec.fuel_type == FuelType.DIESEL_ELECTRIC:
        if spec.is_series_hybrid:
            if spec.dvs_power_greater_than_electric:
                return 'Дизель+Электро (последовательный, ДВС>ЭД)'
            else:
                return 'Дизель+Электро (последовательный, ЭД≥ДВС)'
        else:
            return 'Дизель+Электро (параллельный)'
    elif spec.fuel_type == FuelType.GASOLINE_ELECTRIC:
        if spec.is_series_hybrid:
            if spec.dvs_power_greater_than_electric:
                return 'Бензин+Электро (последовательный, ДВС>ЭД)'
            else:
                return 'Бензин+Электро (последовательный, ЭД≥ДВС)'
        else:
            return 'Бензин+Электро (параллельный)'
    elif spec.engine_type == EngineType.HYBRID_SERIES:
        return 'Гибрид (последовательный)'
    elif spec.engine_type == EngineType.HYBRID_PARALLEL:
        return 'Гибрид (параллельный)'
    else:
        # Для обычных ДВС возвращаем общее "ДВС" для совместимости с тестами
        return 'ДВС'


def format_currency(amount: float) -> str:
    """Форматирование суммы в рублях"""
    return f"{amount:,.0f}".replace(",", " ")


def print_calculation_result(result: CalculationResult):
    """Вывод результатов расчета"""
    bd = result.breakdown

    print("\n" + "=" * 60)
    print("           РАСЧЕТ ТАМОЖЕННЫХ ПЛАТЕЖЕЙ")
    print("=" * 60)
    print(f"Транспортное средство: {bd['vehicle_type_ru']}")
    print(f"Импортер: {bd['importer_type_ru']}")
    print(f"Тип двигателя: {bd['engine_type_ru']}")
    print(f"Стоимость: {bd['cost_original']:,.2f} {bd['currency']} = {format_currency(result.cost_rub)} руб.")

    # Информация о курсах валют
    rates_info = "📈 Курсы ЦБ РФ: "
    if bd['currency'] != 'RUB':
        rates_info += f"{bd['currency']}/RUB = {bd['exchange_rate']:.4f}"
    if bd['currency'] != 'EUR':
        rates_info += f", EUR/RUB = {bd['eur_rate']:.4f}"
    print(rates_info)

    print("\nТАМОЖЕННЫЕ ПЛАТЕЖИ:")
    print(f"• Пошлина: {format_currency(result.duty_rub)} руб. ({bd['duty_eur']:.2f} EUR)")

    if result.excise_rub > 0:
        print(f"• Акциз: {format_currency(result.excise_rub)} руб.")

    if result.vat_rub > 0:
        print(f"• НДС (20%): {format_currency(result.vat_rub)} руб.")

    print(f"• Утилизационный сбор: {format_currency(result.util_fee_rub)} руб.")
    print(f"• Таможенный сбор: {format_currency(result.customs_fee_rub)} руб.")

    print(f"\nИТОГО К ДОПЛАТЕ: {format_currency(result.total_rub)} руб.")

    # Предупреждения
    if result.breakdown['importer_type_ru'] == 'Физлицо (перепродажа)':
        print("\n⚠️  ВНИМАНИЕ: Для перепродажи необходимо оформление ИП или ООО!")

    print("\n📋 Примечание: Расчет выполнен по ставкам 2025 года.")
    print("   Для точного расчета обратитесь к таможенному брокеру.")
    print("=" * 60)


def update_exchange_rates():
    """Принудительное обновление курсов валют"""
    print("🔄 Обновление курсов валют...")
    # Очищаем кэш для принудительного обновления
    RatesFetcher._cache = {}
    RatesFetcher._cache_time = None

    rates = RatesFetcher.get_currency_rates()

    print("💱 Актуальные курсы ЦБ РФ:")
    for currency, rate in rates.items():
        if currency != 'RUB':
            print(f"   {currency}/RUB: {rate:.4f}")
    print()


def _prompt_choice(title: str, choices: list[str], default_index: int = 0) -> str:
    """Универсальный выбор из списка (возвращает значение из списка)."""
    print(f"\n{title}")
    for i, ch in enumerate(choices, start=1):
        mark = " (по умолчанию)" if (i - 1) == default_index else ""
        print(f"  {i}. {ch}{mark}")
    while True:
        raw = input(f"Ваш выбор [1-{len(choices)}]: ").strip()
        if raw == "" and 0 <= default_index < len(choices):
            return choices[default_index]
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(choices):
                return choices[idx - 1]
        print("Некорректный ввод, попробуйте снова.")


def _prompt_number(title: str, cast=float, default: float | None = None) -> float:
    """Запрос числа с приводом типа."""
    while True:
        suffix = f" (по умолчанию: {default})" if default is not None else ""
        raw = input(f"{title}{suffix}: ").strip()
        if raw == "" and default is not None:
            return cast(default)
        try:
            # Поддержка запятой как десятичного разделителя
            raw = raw.replace(',', '.')
            return cast(raw)
        except Exception:
            print("Некорректный ввод, попробуйте снова.")


def _prompt_yes_no(title: str, default: bool = False) -> bool:
    """Запрос ответа да/нет."""
    d = 'Y/n' if default else 'y/N'
    while True:
        raw = input(f"{title} [{d}]: ").strip().lower()
        if raw == '' and default is not None:
            return default
        if raw in ('y', 'yes', 'д', 'да'):
            return True
        if raw in ('n', 'no', 'н', 'нет'):
            return False
        print("Введите 'y' или 'n'.")


def start_interactive() -> VehicleSpec:
    """Интерактивный опрос параметров и сбор VehicleSpec."""
    print("\n=============================================")
    print("     ИНТЕРАКТИВНЫЙ РЕЖИМ КАЛЬКУЛЯТОРА v2")
    print("=============================================\n")

    type_map = {
        'car': VehicleType.CAR,
        'quad': VehicleType.QUAD,
        'snowmobile': VehicleType.SNOWMOBILE,
        'motorcycle': VehicleType.MOTORCYCLE,
    }
    importer_map = {
        'phys_personal': ImporterType.PHYS_PERSONAL,
        'phys_resale': ImporterType.PHYS_RESALE,
        'juridical': ImporterType.JURIDICAL,
    }

    vt = _prompt_choice("Тип транспортного средства", list(type_map.keys()), default_index=0)
    it = _prompt_choice("Тип импортера", list(importer_map.keys()), default_index=0)
    curr = _prompt_choice("Валюта стоимости", ['RUB', 'EUR', 'USD', 'CNY', 'JPY'], default_index=1)
    cost = _prompt_number("Стоимость ТС", float)
    age = int(_prompt_number("Возраст ТС (лет)", int))

    # Базовый выбор топлива/природы двигателя
    base_fuel = _prompt_choice("Тип двигателя (по топливу)",
                               ['gasoline', 'diesel', 'electric', 'diesel_electric', 'gasoline_electric'],
                               default_index=0)

    # Определяем архитектуру двигателя и топливо
    engine_type = EngineType.DVS
    fuel_type = FuelType.GASOLINE
    is_series_hybrid = False
    dvs_power_greater_than_electric = False

    if base_fuel == 'electric':
        engine_type = EngineType.ELECTRIC
        fuel_type = FuelType.ELECTRIC
    elif base_fuel in ['diesel_electric', 'gasoline_electric']:
        # Новые гибридные типы - сразу спрашиваем параметры гибрида
        fuel_type = FuelType.DIESEL_ELECTRIC if base_fuel == 'diesel_electric' else FuelType.GASOLINE_ELECTRIC
        engine_type = EngineType.DVS  # Базовый тип для расчетов

        # Спрашиваем про последовательную установку
        is_series_hybrid = _prompt_yes_no("Силовая установка последовательного типа?", default=False)

        # Спрашиваем про соотношение мощностей (актуально для всех гибридов)
        dvs_power_greater_than_electric = _prompt_yes_no(
            "Мощность ДВС больше максимальной 30-минутной мощности ЭД?", default=False)
    else:
        # gasoline / diesel - обычные ДВС (НЕ гибриды)
        fuel_type = FuelType.GASOLINE if base_fuel == 'gasoline' else FuelType.DIESEL
        engine_type = EngineType.DVS

    # Объем двигателя (для электричек = 0)
    if engine_type == EngineType.ELECTRIC:
        volume = 0
    else:
        volume = int(_prompt_number("Объем двигателя (см³)", int))

    # Мощность запрашиваем для всех типов ТС (нужна для расчета пошлин и акцизов)
    power = 0
    if type_map[vt] in [VehicleType.CAR, VehicleType.MOTORCYCLE, VehicleType.QUAD, VehicleType.SNOWMOBILE]:
        # Для всех ТС мощность важна для расчета пошлин
        power_float = _prompt_number("Мощность (л.с.)", float)
        # Для расчетов используем целое число, округляя вверх для дробных значений
        power = int(power_float) if power_float == int(power_float) else int(power_float) + 1

        # Для гибридных типов используем общую мощность автомобиля
        # Детальные мощности ДВС и ЭД не запрашиваем - они не влияют на расчет

    spec = VehicleSpec(
        vehicle_type=type_map[vt],
        importer_type=importer_map[it],
        cost_original=cost,
        currency=curr,
        age_years=age,
        engine_volume_cc=volume,
        power_hp=power,
        engine_type=engine_type,
        fuel_type=fuel_type,
        is_series_hybrid=is_series_hybrid,
        dvs_power_greater_than_electric=dvs_power_greater_than_electric
    )

    # Валидация простых несоответствий
    if spec.engine_type == EngineType.ELECTRIC and spec.engine_volume_cc != 0:
        logger.warning("Для электро ТС объем двигателя должен быть 0 — исправляю на 0")
        spec.engine_volume_cc = 0

    return spec


def main():
    """Главная функция CLI"""
    parser = argparse.ArgumentParser(
        description='Калькулятор таможенных пошлин РФ v2.0',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:

Автомобиль для физлица:
  python customs_calculator_v2.py --type car --importer phys_personal --cost 10000 --currency EUR --age 2 --volume 2000 --power 150 --engine dvs

Квадроцикл для юрлица:
  python customs_calculator_v2.py --type quad --importer juridical --cost 15000 --currency USD --age 1 --volume 1000 --power 100 --engine dvs

Электроснегоход:
  python customs_calculator_v2.py --type snowmobile --importer phys_resale --cost 8000 --currency EUR --age 1 --volume 0 --power 120 --engine electric

Обновление курсов:
  python customs_calculator_v2.py --update-rates
        """
    )

    parser.add_argument('--type', choices=['car', 'quad', 'snowmobile', 'motorcycle'],
                        help='Тип транспортного средства')
    parser.add_argument('--importer', choices=['phys_personal', 'phys_resale', 'juridical'],
                        help='Тип импортера')
    parser.add_argument('--cost', type=float,
                        help='Стоимость ТС')
    parser.add_argument('--currency', choices=['RUB', 'EUR', 'USD', 'CNY', 'JPY'], default='RUB',
                        help='Валюта стоимости (по умолчанию RUB)')
    parser.add_argument('--age', type=int,
                        help='Возраст ТС в годах')
    parser.add_argument('--volume', type=int,
                        help='Объем двигателя в см³ (0 для электро)')
    parser.add_argument('--power', type=int,
                        help='Мощность в л.с.')
    parser.add_argument('--engine', choices=['dvs', 'electric', 'hybrid', 'hybrid_series', 'hybrid_parallel'],
                        help='Тип двигателя (hybrid = hybrid_parallel для совместимости)')
    parser.add_argument('--fuel',
                        choices=['gasoline', 'diesel', 'electric', 'hybrid', 'diesel_electric', 'gasoline_electric'],
                        default='gasoline',
                        help='Тип топлива для ставок пошлины (primarily for juridical)')
    parser.add_argument('--dvs-power', type=int, default=0,
                        help='Мощность ДВС части для гибридов (л.с.)')
    parser.add_argument('--electric-power', type=int, default=0,
                        help='Мощность электро части для гибридов (л.с.)')
    parser.add_argument('--series-hybrid', action='store_true',
                        help='Силовая установка последовательного типа')
    parser.add_argument('--dvs-greater-electric', action='store_true',
                        help='Мощность ДВС больше максимальной 30-минутной мощности ЭД')
    parser.add_argument('--update-rates', action='store_true',
                        help='Обновить курсы валют и выйти')
    parser.add_argument('--interactive', action='store_true',
                        help='Интерактивный режим (вопросы-ответы)')

    args = parser.parse_args()

    # Обработка обновления курсов
    if args.update_rates:
        update_exchange_rates()
        return

    # Интерактивный режим
    if args.interactive:
        try:
            spec = start_interactive()
            result = calculate_customs_payments(spec)
            print_calculation_result(result)
        except Exception as e:
            import traceback
            logger.error(f"Ошибка интерактивного расчета: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            sys.exit(1)
        return

    # Проверка обязательных аргументов для расчета
    required_args = ['type', 'importer', 'cost', 'age', 'volume', 'power', 'engine']
    missing_args = [arg for arg in required_args if getattr(args, arg) is None]
    if missing_args:
        parser.error(f"Для расчета требуются аргументы: {', '.join('--' + arg for arg in missing_args)}")
        return

    try:
        # Создание спецификации ТС
        engine_type = args.engine
        # Обратная совместимость: hybrid -> hybrid_parallel
        if engine_type == 'hybrid':
            engine_type = 'hybrid_parallel'

        spec = VehicleSpec(
            vehicle_type=VehicleType(args.type),
            importer_type=ImporterType(args.importer),
            cost_original=args.cost,
            currency=args.currency,
            age_years=args.age,
            engine_volume_cc=args.volume,
            power_hp=args.power,
            engine_type=EngineType(engine_type),
            dvs_power_hp=args.dvs_power,
            electric_power_hp=args.electric_power,
            fuel_type=FuelType(args.fuel),
            is_series_hybrid=args.series_hybrid,
            dvs_power_greater_than_electric=args.dvs_greater_electric
        )

        # Валидация
        if spec.engine_type == EngineType.ELECTRIC and spec.engine_volume_cc != 0:
            logger.warning("Для электро ТС объем двигателя должен быть 0")
            spec.engine_volume_cc = 0

        # Расчет
        result = calculate_customs_payments(spec)

        # Вывод результата
        print_calculation_result(result)

    except Exception as e:
        logger.error(f"Ошибка расчета: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
