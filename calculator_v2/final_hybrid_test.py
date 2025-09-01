#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Финальный тест новых гибридных типов автомобилей
Демонстрирует все возможные сценарии расчета
"""

import sys
sys.path.append('.')

from customs_calculator_v5 import (
    VehicleSpec, VehicleType, ImporterType, EngineType, FuelType,
    calculate_customs_payments
)

def format_currency(amount: float) -> str:
    """Форматирование суммы в рублях"""
    return f"{amount:,.0f}".replace(",", " ")

def test_all_hybrid_scenarios():
    """Тестирование всех сценариев новых гибридных типов"""
    
    print("=" * 100)
    print("ФИНАЛЬНЫЙ ТЕСТ НОВЫХ ГИБРИДНЫХ ТИПОВ АВТОМОБИЛЕЙ")
    print("=" * 100)
    
    scenarios = [
        {
            'name': 'Дизель+Электро (последовательный, ЭД≥ДВС) - как ЭЛЕКТРО',
            'spec': VehicleSpec(
                vehicle_type=VehicleType.CAR,
                importer_type=ImporterType.PHYS_PERSONAL,
                cost_original=25000, currency='EUR', age_years=2,
                engine_volume_cc=2000, power_hp=200, engine_type=EngineType.DVS,
                dvs_power_hp=90, electric_power_hp=130,
                fuel_type=FuelType.DIESEL_ELECTRIC,
                is_series_hybrid=True, dvs_power_greater_than_electric=False
            )
        },
        {
            'name': 'Дизель+Электро (последовательный, ДВС>ЭД) - как ДВС',
            'spec': VehicleSpec(
                vehicle_type=VehicleType.CAR,
                importer_type=ImporterType.PHYS_PERSONAL,
                cost_original=25000, currency='EUR', age_years=2,
                engine_volume_cc=2000, power_hp=200, engine_type=EngineType.DVS,
                dvs_power_hp=130, electric_power_hp=90,
                fuel_type=FuelType.DIESEL_ELECTRIC,
                is_series_hybrid=True, dvs_power_greater_than_electric=True
            )
        },
        {
            'name': 'Дизель+Электро (параллельный) - как ДВС',
            'spec': VehicleSpec(
                vehicle_type=VehicleType.CAR,
                importer_type=ImporterType.PHYS_PERSONAL,
                cost_original=25000, currency='EUR', age_years=2,
                engine_volume_cc=2000, power_hp=200, engine_type=EngineType.DVS,
                dvs_power_hp=130, electric_power_hp=90,
                fuel_type=FuelType.DIESEL_ELECTRIC,
                is_series_hybrid=False, dvs_power_greater_than_electric=True
            )
        },
        {
            'name': 'Бензин+Электро (последовательный, ЭД≥ДВС) - как ЭЛЕКТРО',
            'spec': VehicleSpec(
                vehicle_type=VehicleType.CAR,
                importer_type=ImporterType.PHYS_PERSONAL,
                cost_original=25000, currency='EUR', age_years=2,
                engine_volume_cc=2000, power_hp=200, engine_type=EngineType.DVS,
                dvs_power_hp=90, electric_power_hp=130,
                fuel_type=FuelType.GASOLINE_ELECTRIC,
                is_series_hybrid=True, dvs_power_greater_than_electric=False
            )
        },
        {
            'name': 'Бензин+Электро (последовательный, ДВС>ЭД) - как ДВС',
            'spec': VehicleSpec(
                vehicle_type=VehicleType.CAR,
                importer_type=ImporterType.PHYS_PERSONAL,
                cost_original=25000, currency='EUR', age_years=2,
                engine_volume_cc=2000, power_hp=200, engine_type=EngineType.DVS,
                dvs_power_hp=130, electric_power_hp=90,
                fuel_type=FuelType.GASOLINE_ELECTRIC,
                is_series_hybrid=True, dvs_power_greater_than_electric=True
            )
        },
        {
            'name': 'Бензин+Электро (параллельный) - как ДВС',
            'spec': VehicleSpec(
                vehicle_type=VehicleType.CAR,
                importer_type=ImporterType.PHYS_PERSONAL,
                cost_original=25000, currency='EUR', age_years=2,
                engine_volume_cc=2000, power_hp=200, engine_type=EngineType.DVS,
                dvs_power_hp=130, electric_power_hp=90,
                fuel_type=FuelType.GASOLINE_ELECTRIC,
                is_series_hybrid=False, dvs_power_greater_than_electric=True
            )
        },
        {
            'name': 'Юрлицо: Дизель+Электро (последовательный, ЭД≥ДВС) - как ЭЛЕКТРО',
            'spec': VehicleSpec(
                vehicle_type=VehicleType.CAR,
                importer_type=ImporterType.JURIDICAL,
                cost_original=25000, currency='EUR', age_years=2,
                engine_volume_cc=2000, power_hp=200, engine_type=EngineType.DVS,
                dvs_power_hp=90, electric_power_hp=130,
                fuel_type=FuelType.DIESEL_ELECTRIC,
                is_series_hybrid=True, dvs_power_greater_than_electric=False
            )
        },
        {
            'name': 'Юрлицо: Бензин+Электро (параллельный) - как ДВС',
            'spec': VehicleSpec(
                vehicle_type=VehicleType.CAR,
                importer_type=ImporterType.JURIDICAL,
                cost_original=25000, currency='EUR', age_years=2,
                engine_volume_cc=2000, power_hp=200, engine_type=EngineType.DVS,
                dvs_power_hp=130, electric_power_hp=90,
                fuel_type=FuelType.GASOLINE_ELECTRIC,
                is_series_hybrid=False, dvs_power_greater_than_electric=True
            )
        }
    ]
    
    results = []
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        print("-" * 80)
        
        result = calculate_customs_payments(scenario['spec'])
        results.append(result)
        
        print(f"Тип двигателя: {result.breakdown['engine_type_ru']}")
        print(f"Акциз: {format_currency(result.excise_rub)} руб.")
        print(f"Пошлина: {format_currency(result.duty_rub)} руб.")
        print(f"НДС: {format_currency(result.vat_rub)} руб.")
        print(f"Утилизационный сбор: {format_currency(result.util_fee_rub)} руб.")
        print(f"ИТОГО: {format_currency(result.total_rub)} руб.")
    
    # Сводная таблица
    print("\n" + "=" * 100)
    print("СВОДНАЯ ТАБЛИЦА РЕЗУЛЬТАТОВ")
    print("=" * 100)
    print(f"{'№':<2} {'Сценарий':<50} {'Акциз':<12} {'Пошлина':<12} {'НДС':<12} {'Итого':<15}")
    print("-" * 100)
    
    for i, (scenario, result) in enumerate(zip(scenarios, results), 1):
        name = scenario['name'][:47] + "..." if len(scenario['name']) > 50 else scenario['name']
        print(f"{i:<2} {name:<50} {result.excise_rub:<12,.0f} {result.duty_rub:<12,.0f} {result.vat_rub:<12,.0f} {result.total_rub:<15,.0f}")
    
    print("\n" + "=" * 100)
    print("ВЫВОДЫ:")
    print("• Последовательный гибрид с ЭД≥ДВС считается как электромобиль (акциз по ЭД, пошлина 15%, НДС 20%)")
    print("• Последовательный гибрид с ДВС>ЭД считается как ДВС (акциз по ДВС, пошлина по объему)")
    print("• Параллельный гибрид всегда считается как ДВС")
    print("• Для физлиц личное использование: акциз на ДВС = 0, на электро > 0")
    print("• Для юрлиц: всегда НДС 20%, акциз по мощности")
    print("=" * 100)

if __name__ == "__main__":
    test_all_hybrid_scenarios()