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

import sys
import argparse
import logging
import requests
import datetime
from typing import Dict, Any, Optional, Tuple
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
                    {'max_cc': 1000, 'coeff': 9.91},
                    {'max_cc': 2000, 'coeff': 33.37},  # 1001-2000 см³
                    {'max_cc': 3000, 'coeff': 103.15},
                    {'max_cc': 3500, 'coeff': 118.44},
                    {'max_cc': float('inf'), 'coeff': 150.82}
                ],
                'old_dvs_by_volume': [
                    {'max_cc': 1000, 'coeff': 25.3},
                    {'max_cc': 2000, 'coeff': 64.57},
                    {'max_cc': 3000, 'coeff': 156.17},
                    {'max_cc': 3500, 'coeff': 236.87},
                    {'max_cc': float('inf'), 'coeff': 301.64}
                ],
                'new_electric': 1.42, 'old_electric': 2.84,  # Актуальные коэффициенты для электро
                'new_hybrid': 1.42, 'old_hybrid': 2.84    # Как для электро
            },
            'quad': {'new': 1.63, 'old': 6.1},
            'snowmobile': {'new': 1.63, 'old': 6.1},
            'motorcycle': {'new': 1.63, 'old': 6.1}
        }
    },
    
    # Пошлины для автомобилей (%) - актуальные ставки 2025
    'CAR_DUTY': {
        'commercial': {
            # Для юридических лиц
            'gasoline': {'new': 0.15, 'old': 0.20},  # бензиновые
            'diesel': {'new': 0.15, 'old': 0.20},    # дизельные  
            'electric': {'new': 0.15, 'old': 0.15},  # электро - льготная ставка
            'hybrid': {'new': 0.15, 'old': 0.18},    # гибрид - промежуточная ставка
            # Минимальные ставки EUR/см³
            'min_rates': {
                'gasoline': {'new': 0.36, 'old': 1.4},
                'diesel': {'new': 0.32, 'old': 1.5}, 
                'electric': {'new': 0.0, 'old': 0.0},   # без минимума для электро
                'hybrid': {'new': 0.30, 'old': 1.2}     # льготный минимум для гибрида
            }
        },
        'personal_ets': {
            # ЕТС для физлиц (личное использование и перепродажа)
            'under_3': [
                {'max_value_eur': 8500, 'rate': 0.54, 'min_eur_cc': 2.5},
                {'max_value_eur': 16700, 'rate': 0.48, 'min_eur_cc': 3.5},
                {'max_value_eur': 42300, 'rate': 0.48, 'min_eur_cc': 5.5},
                {'max_value_eur': 84500, 'rate': 0.48, 'min_eur_cc': 7.5},
                {'max_value_eur': 169000, 'rate': 0.48, 'min_eur_cc': 15.0},
                {'max_value_eur': float('inf'), 'rate': 0.48, 'min_eur_cc': 20.0}
            ],
            'over_3': [
                {'max_cc': 1000, 'rate_eur_cc': 3.0},
                {'max_cc': 1500, 'rate_eur_cc': 3.2},
                {'max_cc': 1800, 'rate_eur_cc': 3.5},
                {'max_cc': 2300, 'rate_eur_cc': 4.8},
                {'max_cc': 3000, 'rate_eur_cc': 5.0},
                {'max_cc': float('inf'), 'rate_eur_cc': 5.7}
            ],
            # Льготы для электро и гибридов (физлица)
            'electric_hybrid': {
                'under_3': {'rate': 0.15, 'min_eur_cc': 0.0},  # льготная ставка
                'over_3': {'rate_eur_cc': 1.0}  # льготная ставка EUR/см³
            }
        }
    },
    
    # Пошлины для мотоциклов (%)
    'MOTORCYCLE_DUTY': {
        'commercial': {'rate': 0.15, 'min_eur_cc': 0.8},  # 15% но не менее 0.8 EUR/см³
        'personal': {'rate': 0.15, 'min_eur_cc': 0.5}     # льготы для физлиц
    },
    
    # Пошлины для квадроциклов (%)
    'QUAD_DUTY': {
        'new': 0.30,  # до 3 лет
        'old': 0.35,  # старше 3 лет
        'min_eur_cc': {'new': 1.2, 'old': 1.5}
    },
    
    # Пошлины для снегоходов (%)
    'SNOWMOBILE_DUTY': {
        'rate': 0.05,  # 5% независимо от возраста
        'min_eur_cc': 0  # минимума нет
    },
    
    # НДС
    'VAT_RATE': 0.20,
    
    # Таможенные сборы (руб) - актуальные ставки 2025
    'CUSTOMS_FEES': [
        {'max_value_rub': 200000, 'fee': 775},
        {'max_value_rub': 450000, 'fee': 1550},
        {'max_value_rub': 1200000, 'fee': 4269},  # Исправлено для диапазона до 1.2 млн
        {'max_value_rub': 2700000, 'fee': 8538},
        {'max_value_rub': 4200000, 'fee': 12015},
        {'max_value_rub': 5500000, 'fee': 15500},
        {'max_value_rub': 7000000, 'fee': 20023},
        {'max_value_rub': 10000000, 'fee': 21800},
        {'max_value_rub': float('inf'), 'fee': 21800}
    ]
}

def find_rate_by_value(value: float, rates_table: list, key: str) -> dict:
    """Поиск ставки по значению в таблице"""
    for rate in rates_table:
        if value <= rate.get(key, float('inf')):
            return rate
    return rates_table[-1]

def calc_excise(spec: VehicleSpec) -> float:
    """Расчет акциза с учетом типа двигателя и актуальных ставок 2025"""
    
    if spec.engine_type == EngineType.ELECTRIC:
        # Для электромобилей - актуальные ставки с 01.01.2025
        power_hp = spec.power_hp
        
        if power_hp <= 90:
            return 0.0  # Льгота до 90 л.с.
        elif power_hp <= 150:
            return power_hp * 61
        elif power_hp <= 200:
            return power_hp * 583
        elif power_hp <= 300:
            return power_hp * 955
        elif power_hp <= 400:
            return power_hp * 1628
        elif power_hp <= 500:
            return power_hp * 1685
        else:
            return power_hp * 1740
    
    elif spec.engine_type == EngineType.HYBRID_SERIES:
        # Последовательный гибрид - акциз с суммы мощностей ДВС + электро
        total_power = spec.dvs_power_hp + spec.electric_power_hp
        
        # Применяем ставки как для электромобилей
        if total_power <= 90:
            return 0.0
        elif total_power <= 150:
            return total_power * 61
        elif total_power <= 200:
            return total_power * 583
        else:
            # Продолжаем по обычной шкале
            rate_info = find_rate_by_value(total_power, RATES_2025['EXCISE_RATES'], 'max_hp')
            return total_power * rate_info['rate']
    
    elif spec.engine_type == EngineType.HYBRID_PARALLEL:
        # Параллельный гибрид - акциз только с мощности ДВС
        dvs_power = spec.dvs_power_hp if spec.dvs_power_hp > 0 else int(spec.power_hp * 0.65)
        rate_info = find_rate_by_value(dvs_power, RATES_2025['EXCISE_RATES'], 'max_hp')
        return dvs_power * rate_info['rate']
    
    else:
        # Для ДВС обычный расчет
        rate_info = find_rate_by_value(spec.power_hp, RATES_2025['EXCISE_RATES'], 'max_hp')
        return spec.power_hp * rate_info['rate']

def calc_util_fee(vehicle_type: VehicleType, importer_type: ImporterType, 
                  age_years: int, engine_type: EngineType, engine_volume_cc: int) -> float:
    """Расчет утилизационного сбора"""
    vehicle_key = vehicle_type.value
    is_new = age_years < 3
    age_key = 'new' if is_new else 'old'
    
    base_rate = RATES_2025['UTIL_BASE'][vehicle_key]
    
    if importer_type == ImporterType.PHYS_PERSONAL:
        # Для физлиц личное использование
        if vehicle_key == 'car':
            # Фиксированные суммы для автомобилей
            return RATES_2025['UTIL_COEFFS']['personal'][vehicle_key][age_key]
        else:
            # Для квадроциклов и снегоходов
            coeff = RATES_2025['UTIL_COEFFS']['personal'][vehicle_key][age_key]
            return base_rate * coeff
    else:
        # Коммерческое использование
        if vehicle_key == 'car':
            if engine_type == EngineType.ELECTRIC:
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
    """Расчет таможенного сбора"""
    if importer_type == ImporterType.PHYS_PERSONAL:
        return 500.0  # Фиксированная ставка для физлиц личное использование
    
    rate_info = find_rate_by_value(cost_rub, RATES_2025['CUSTOMS_FEES'], 'max_value_rub')
    return rate_info['fee']

def calc_car_duty(spec: VehicleSpec, cost_eur: float) -> float:
    """Расчет пошлины для автомобилей с учетом типа двигателя"""
    # Для физлиц (и личное, и перепродажа) применяется ЕТС система
    if spec.importer_type in [ImporterType.PHYS_PERSONAL, ImporterType.PHYS_RESALE]:
        # Льготы для электро и последовательных гибридов
        if spec.engine_type in [EngineType.ELECTRIC, EngineType.HYBRID_SERIES]:
            if spec.age_years < 3:
                # Льготная ставка для новых электро/последовательных гибридов
                rate = RATES_2025['CAR_DUTY']['personal_ets']['electric_hybrid']['under_3']['rate']
                min_eur_cc = RATES_2025['CAR_DUTY']['personal_ets']['electric_hybrid']['under_3']['min_eur_cc']
                duty_by_value = cost_eur * rate
                duty_by_volume = spec.engine_volume_cc * min_eur_cc
                return max(duty_by_value, duty_by_volume)
            else:
                # Льготная ставка для старых электро/последовательных гибридов
                rate_eur_cc = RATES_2025['CAR_DUTY']['personal_ets']['electric_hybrid']['over_3']['rate_eur_cc']
                return spec.engine_volume_cc * rate_eur_cc
        
        # Обычная ЕТС для ДВС и параллельных гибридов
        if spec.age_years < 3:
            # ЕТС для новых авто - по стоимости
            rate_info = find_rate_by_value(cost_eur, 
                                         RATES_2025['CAR_DUTY']['personal_ets']['under_3'], 
                                         'max_value_eur')
            duty_by_value = cost_eur * rate_info['rate']
            duty_by_volume = spec.engine_volume_cc * rate_info['min_eur_cc']
            return max(duty_by_value, duty_by_volume)
        else:
            # ЕТС для старых авто - по объему двигателя
            rate_info = find_rate_by_value(spec.engine_volume_cc,
                                         RATES_2025['CAR_DUTY']['personal_ets']['over_3'],
                                         'max_cc')
            return spec.engine_volume_cc * rate_info['rate_eur_cc']
    else:
        # Для юридических лиц - коммерческие ставки по типу двигателя
        age_key = 'new' if spec.age_years < 3 else 'old'
        
        # Определяем тип двигателя для ставок
        if spec.engine_type == EngineType.ELECTRIC:
            # Электромобили - фиксированная ставка 15%
            return cost_eur * 0.15
        elif spec.engine_type == EngineType.HYBRID_SERIES:
            # Последовательные гибриды - как электромобили, 15%
            return cost_eur * 0.15
        elif spec.engine_type == EngineType.HYBRID_PARALLEL:
            # Параллельные гибриды - по обычным ставкам от объема двигателя
            engine_key = 'gasoline'  # Можно добавить параметр fuel_type
            rate = RATES_2025['CAR_DUTY']['commercial'][engine_key][age_key]
            min_rate_eur_cc = RATES_2025['CAR_DUTY']['commercial']['min_rates'][engine_key][age_key]
            
            duty_by_value = cost_eur * rate
            duty_by_volume = spec.engine_volume_cc * min_rate_eur_cc
            
            return max(duty_by_value, duty_by_volume)
        else:
            # ДВС - обычные ставки
            engine_key = 'gasoline'  # Можно добавить параметр fuel_type
            rate = RATES_2025['CAR_DUTY']['commercial'][engine_key][age_key]
            min_rate_eur_cc = RATES_2025['CAR_DUTY']['commercial']['min_rates'][engine_key][age_key]
            
            duty_by_value = cost_eur * rate
            duty_by_volume = spec.engine_volume_cc * min_rate_eur_cc
            
            return max(duty_by_value, duty_by_volume)

def calc_quad_duty(spec: VehicleSpec, cost_eur: float) -> float:
    """Расчет пошлины для квадроциклов"""
    age_key = 'new' if spec.age_years < 3 else 'old'
    rate = RATES_2025['QUAD_DUTY'][age_key]
    min_eur_cc = RATES_2025['QUAD_DUTY']['min_eur_cc'][age_key]
    
    duty_by_value = cost_eur * rate
    duty_by_volume = spec.engine_volume_cc * min_eur_cc
    
    return max(duty_by_value, duty_by_volume)

def calc_snowmobile_duty(spec: VehicleSpec, cost_eur: float) -> float:
    """Расчет пошлины для снегоходов"""
    return cost_eur * RATES_2025['SNOWMOBILE_DUTY']['rate']

def calc_motorcycle_duty(spec: VehicleSpec, cost_eur: float) -> float:
    """Расчет пошлины для мотоциклов"""
    if spec.importer_type == ImporterType.PHYS_PERSONAL:
        # Льготы для физлиц
        rate = RATES_2025['MOTORCYCLE_DUTY']['personal']['rate']
        min_eur_cc = RATES_2025['MOTORCYCLE_DUTY']['personal']['min_eur_cc']
    else:
        # Коммерческие ставки
        rate = RATES_2025['MOTORCYCLE_DUTY']['commercial']['rate']
        min_eur_cc = RATES_2025['MOTORCYCLE_DUTY']['commercial']['min_eur_cc']
    
    duty_by_value = cost_eur * rate
    duty_by_volume = spec.engine_volume_cc * min_eur_cc
    
    return max(duty_by_value, duty_by_volume)

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
    
    # Акциз (для коммерческого использования и всех типов двигателей)
    excise_rub = 0.0
    if spec.importer_type != ImporterType.PHYS_PERSONAL:
        excise_rub = calc_excise(spec)
    
    # НДС (только для коммерческого использования)
    vat_rub = 0.0
    if spec.importer_type != ImporterType.PHYS_PERSONAL:
        vat_base = cost_rub + duty_rub + excise_rub
        vat_rub = vat_base * RATES_2025['VAT_RATE']
    
    # Утилизационный сбор
    util_fee_rub = calc_util_fee(spec.vehicle_type, spec.importer_type, 
                                spec.age_years, spec.engine_type, spec.engine_volume_cc)
    
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
        'engine_type_ru': {
            EngineType.DVS: 'ДВС',
            EngineType.ELECTRIC: 'Электро',
            EngineType.HYBRID_SERIES: 'Гибрид (последовательный)',
            EngineType.HYBRID_PARALLEL: 'Гибрид (параллельный)'
        }[spec.engine_type]
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
    parser.add_argument('--dvs-power', type=int, default=0,
                       help='Мощность ДВС части для гибридов (л.с.)')
    parser.add_argument('--electric-power', type=int, default=0,
                       help='Мощность электро части для гибридов (л.с.)')
    parser.add_argument('--update-rates', action='store_true',
                       help='Обновить курсы валют и выйти')
    
    args = parser.parse_args()
    
    # Обработка обновления курсов
    if args.update_rates:
        update_exchange_rates()
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
            electric_power_hp=args.electric_power
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