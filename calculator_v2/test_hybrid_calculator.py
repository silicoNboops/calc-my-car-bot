#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест нового функционала гибридных автомобилей
"""

import sys
sys.path.append('.')

from customs_calculator_v5 import (
    VehicleSpec, VehicleType, ImporterType, EngineType, FuelType,
    calculate_customs_payments, print_calculation_result
)

def test_hybrid_scenarios():
    """Тестирование различных сценариев гибридных автомобилей"""
    
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ НОВЫХ ГИБРИДНЫХ СЦЕНАРИЕВ")
    print("=" * 80)
    
    # Сценарий 1: Последовательный гибрид, ЭД ≥ ДВС (считаем как электромобиль)
    print("\n1. ПОСЛЕДОВАТЕЛЬНЫЙ ГИБРИД: ЭД ≥ ДВС (как электромобиль)")
    print("-" * 60)
    spec1 = VehicleSpec(
        vehicle_type=VehicleType.CAR,
        importer_type=ImporterType.PHYS_PERSONAL,
        cost_original=25000,
        currency='EUR',
        age_years=2,
        engine_volume_cc=2000,
        power_hp=200,
        engine_type=EngineType.DVS,
        dvs_power_hp=120,
        electric_power_hp=100,
        fuel_type=FuelType.GASOLINE_ELECTRIC,
        is_series_hybrid=True,
        dvs_power_greater_than_electric=False  # ЭД ≥ ДВС
    )
    result1 = calculate_customs_payments(spec1)
    print_calculation_result(result1)
    
    # Сценарий 2: Последовательный гибрид, ДВС > ЭД (считаем как ДВС)
    print("\n2. ПОСЛЕДОВАТЕЛЬНЫЙ ГИБРИД: ДВС > ЭД (как ДВС)")
    print("-" * 60)
    spec2 = VehicleSpec(
        vehicle_type=VehicleType.CAR,
        importer_type=ImporterType.PHYS_PERSONAL,
        cost_original=25000,
        currency='EUR',
        age_years=2,
        engine_volume_cc=2000,
        power_hp=200,
        engine_type=EngineType.DVS,
        dvs_power_hp=120,
        electric_power_hp=100,
        fuel_type=FuelType.GASOLINE_ELECTRIC,
        is_series_hybrid=True,
        dvs_power_greater_than_electric=True  # ДВС > ЭД
    )
    result2 = calculate_customs_payments(spec2)
    print_calculation_result(result2)
    
    # Сценарий 3: Параллельный гибрид (считаем как ДВС)
    print("\n3. ПАРАЛЛЕЛЬНЫЙ ГИБРИД (как ДВС)")
    print("-" * 60)
    spec3 = VehicleSpec(
        vehicle_type=VehicleType.CAR,
        importer_type=ImporterType.PHYS_PERSONAL,
        cost_original=25000,
        currency='EUR',
        age_years=2,
        engine_volume_cc=2000,
        power_hp=200,
        engine_type=EngineType.DVS,
        dvs_power_hp=120,
        electric_power_hp=100,
        fuel_type=FuelType.DIESEL_ELECTRIC,
        is_series_hybrid=False,  # Параллельный
        dvs_power_greater_than_electric=False
    )
    result3 = calculate_customs_payments(spec3)
    print_calculation_result(result3)
    
    # Сценарий 4: Для юридического лица (последовательный, ЭД ≥ ДВС)
    print("\n4. ЮРИДИЧЕСКОЕ ЛИЦО: Последовательный гибрид, ЭД ≥ ДВС")
    print("-" * 60)
    spec4 = VehicleSpec(
        vehicle_type=VehicleType.CAR,
        importer_type=ImporterType.JURIDICAL,
        cost_original=25000,
        currency='EUR',
        age_years=2,
        engine_volume_cc=2000,
        power_hp=200,
        engine_type=EngineType.DVS,
        dvs_power_hp=120,
        electric_power_hp=100,
        fuel_type=FuelType.GASOLINE_ELECTRIC,
        is_series_hybrid=True,
        dvs_power_greater_than_electric=False  # ЭД ≥ ДВС
    )
    result4 = calculate_customs_payments(spec4)
    print_calculation_result(result4)
    
    print("\n" + "=" * 80)
    print("СВОДНАЯ ТАБЛИЦА РЕЗУЛЬТАТОВ")
    print("=" * 80)
    print(f"{'Сценарий':<40} {'Акциз':<12} {'Пошлина':<12} {'НДС':<12} {'Утил.сбор':<12}")
    print("-" * 80)
    print(f"{'1. Последовательный, ЭД ≥ ДВС':<40} {result1.excise_rub:<12,.0f} {result1.duty_rub:<12,.0f} {result1.vat_rub:<12,.0f} {result1.util_fee_rub:<12,.0f}")
    print(f"{'2. Последовательный, ДВС > ЭД':<40} {result2.excise_rub:<12,.0f} {result2.duty_rub:<12,.0f} {result2.vat_rub:<12,.0f} {result2.util_fee_rub:<12,.0f}")
    print(f"{'3. Параллельный гибрид':<40} {result3.excise_rub:<12,.0f} {result3.duty_rub:<12,.0f} {result3.vat_rub:<12,.0f} {result3.util_fee_rub:<12,.0f}")
    print(f"{'4. Юрлицо, последовательный ЭД≥ДВС':<40} {result4.excise_rub:<12,.0f} {result4.duty_rub:<12,.0f} {result4.vat_rub:<12,.0f} {result4.util_fee_rub:<12,.0f}")

if __name__ == "__main__":
    test_hybrid_scenarios()