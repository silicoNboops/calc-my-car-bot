#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест интерактивной логики для новых гибридных типов
"""

import sys
sys.path.append('.')

from customs_calculator_v6 import (
    VehicleSpec, VehicleType, ImporterType, EngineType, FuelType,
    calculate_customs_payments, print_calculation_result
)

def test_new_hybrid_logic():
    """Тестирование новой логики гибридных типов"""
    
    print("=" * 80)
    print("ТЕСТ НОВОЙ ЛОГИКИ ГИБРИДНЫХ ТИПОВ")
    print("=" * 80)
    
    # Тест 1: diesel_electric с последовательной установкой, ДВС > ЭД
    print("\n1. ДИЗЕЛЬ+ЭЛЕКТРО: Последовательный, ДВС > ЭД")
    print("-" * 60)
    spec1 = VehicleSpec(
        vehicle_type=VehicleType.CAR,
        importer_type=ImporterType.PHYS_PERSONAL,
        cost_original=30000,
        currency='EUR',
        age_years=2,
        engine_volume_cc=2000,
        power_hp=200,
        engine_type=EngineType.DVS,
        dvs_power_hp=130,
        electric_power_hp=90,
        fuel_type=FuelType.DIESEL_ELECTRIC,
        is_series_hybrid=True,
        dvs_power_greater_than_electric=True
    )
    result1 = calculate_customs_payments(spec1)
    print(f"Тип двигателя: {result1.breakdown['engine_type_ru']}")
    print(f"Акциз: {result1.excise_rub:,.0f} руб.")
    print(f"Пошлина: {result1.duty_rub:,.0f} руб.")
    print(f"НДС: {result1.vat_rub:,.0f} руб.")
    
    # Тест 2: gasoline_electric с параллельной установкой
    print("\n2. БЕНЗИН+ЭЛЕКТРО: Параллельный")
    print("-" * 60)
    spec2 = VehicleSpec(
        vehicle_type=VehicleType.CAR,
        importer_type=ImporterType.PHYS_PERSONAL,
        cost_original=30000,
        currency='EUR',
        age_years=2,
        engine_volume_cc=2000,
        power_hp=200,
        engine_type=EngineType.DVS,
        dvs_power_hp=130,
        electric_power_hp=90,
        fuel_type=FuelType.GASOLINE_ELECTRIC,
        is_series_hybrid=False,  # Параллельный
        dvs_power_greater_than_electric=True
    )
    result2 = calculate_customs_payments(spec2)
    print(f"Тип двигателя: {result2.breakdown['engine_type_ru']}")
    print(f"Акциз: {result2.excise_rub:,.0f} руб.")
    print(f"Пошлина: {result2.duty_rub:,.0f} руб.")
    print(f"НДС: {result2.vat_rub:,.0f} руб.")
    
    # Тест 3: gasoline_electric с последовательной установкой, ЭД ≥ ДВС
    print("\n3. БЕНЗИН+ЭЛЕКТРО: Последовательный, ЭД ≥ ДВС")
    print("-" * 60)
    spec3 = VehicleSpec(
        vehicle_type=VehicleType.CAR,
        importer_type=ImporterType.PHYS_PERSONAL,
        cost_original=30000,
        currency='EUR',
        age_years=2,
        engine_volume_cc=2000,
        power_hp=200,
        engine_type=EngineType.DVS,
        dvs_power_hp=90,
        electric_power_hp=130,
        fuel_type=FuelType.GASOLINE_ELECTRIC,
        is_series_hybrid=True,
        dvs_power_greater_than_electric=False  # ЭД ≥ ДВС
    )
    result3 = calculate_customs_payments(spec3)
    print(f"Тип двигателя: {result3.breakdown['engine_type_ru']}")
    print(f"Акциз: {result3.excise_rub:,.0f} руб.")
    print(f"Пошлина: {result3.duty_rub:,.0f} руб.")
    print(f"НДС: {result3.vat_rub:,.0f} руб.")
    
    print("\n" + "=" * 80)
    print("ПРОВЕРКА ЛОГИКИ:")
    print("1. Дизель+Электро (последовательный, ДВС>ЭД) → считается как ДВС")
    print("2. Бензин+Электро (параллельный) → считается как ДВС") 
    print("3. Бензин+Электро (последовательный, ЭД≥ДВС) → считается как электромобиль")
    print("=" * 80)

if __name__ == "__main__":
    test_new_hybrid_logic()