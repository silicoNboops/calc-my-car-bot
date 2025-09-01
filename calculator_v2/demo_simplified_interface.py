#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Демонстрация упрощенного интерфейса для гибридных автомобилей
"""

import sys
sys.path.append('.')

from customs_calculator_v6 import (
    VehicleSpec, VehicleType, ImporterType, EngineType, FuelType,
    calculate_customs_payments
)

def demo_simplified_interface():
    """Демонстрация упрощенного интерфейса"""
    
    print("=" * 90)
    print("ДЕМОНСТРАЦИЯ УПРОЩЕННОГО ИНТЕРФЕЙСА ДЛЯ ГИБРИДНЫХ АВТОМОБИЛЕЙ")
    print("=" * 90)
    
    print("\n🎯 ОСНОВНЫЕ УПРОЩЕНИЯ:")
    print("• Выбор типа топлива автоматически определяет, гибрид это или нет")
    print("• Для гибридов НЕТ вопросов про отдельные мощности ДВС и ЭД")
    print("• Только 2 ключевых вопроса для определения логики расчета")
    
    scenarios = [
        {
            'title': '🚗 ОБЫЧНЫЙ БЕНЗИНОВЫЙ АВТОМОБИЛЬ',
            'description': 'gasoline → обычный ДВС, никаких дополнительных вопросов',
            'spec': VehicleSpec(
                vehicle_type=VehicleType.CAR, importer_type=ImporterType.PHYS_PERSONAL,
                cost_original=25000, currency='EUR', age_years=2,
                engine_volume_cc=2000, power_hp=200, engine_type=EngineType.DVS,
                fuel_type=FuelType.GASOLINE
            )
        },
        {
            'title': '⚡ ЭЛЕКТРОМОБИЛЬ',
            'description': 'electric → электромобиль, никаких дополнительных вопросов',
            'spec': VehicleSpec(
                vehicle_type=VehicleType.CAR, importer_type=ImporterType.PHYS_PERSONAL,
                cost_original=25000, currency='EUR', age_years=2,
                engine_volume_cc=0, power_hp=200, engine_type=EngineType.ELECTRIC,
                fuel_type=FuelType.ELECTRIC
            )
        },
        {
            'title': '🔋 ГИБРИД: Бензин+Электро (последовательный, ЭД≥ДВС)',
            'description': 'gasoline_electric → автоматически гибрид + 2 вопроса',
            'spec': VehicleSpec(
                vehicle_type=VehicleType.CAR, importer_type=ImporterType.PHYS_PERSONAL,
                cost_original=25000, currency='EUR', age_years=2,
                engine_volume_cc=2000, power_hp=200, engine_type=EngineType.DVS,
                fuel_type=FuelType.GASOLINE_ELECTRIC,
                is_series_hybrid=True, dvs_power_greater_than_electric=False
            )
        },
        {
            'title': '🔋 ГИБРИД: Дизель+Электро (последовательный, ДВС>ЭД)',
            'description': 'diesel_electric → автоматически гибрид + 2 вопроса',
            'spec': VehicleSpec(
                vehicle_type=VehicleType.CAR, importer_type=ImporterType.PHYS_PERSONAL,
                cost_original=25000, currency='EUR', age_years=2,
                engine_volume_cc=2000, power_hp=200, engine_type=EngineType.DVS,
                fuel_type=FuelType.DIESEL_ELECTRIC,
                is_series_hybrid=True, dvs_power_greater_than_electric=True
            )
        },
        {
            'title': '🔋 ГИБРИД: Бензин+Электро (параллельный)',
            'description': 'gasoline_electric → автоматически гибрид + 2 вопроса',
            'spec': VehicleSpec(
                vehicle_type=VehicleType.CAR, importer_type=ImporterType.PHYS_PERSONAL,
                cost_original=25000, currency='EUR', age_years=2,
                engine_volume_cc=2000, power_hp=200, engine_type=EngineType.DVS,
                fuel_type=FuelType.GASOLINE_ELECTRIC,
                is_series_hybrid=False, dvs_power_greater_than_electric=True
            )
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. {scenario['title']}")
        print(f"   {scenario['description']}")
        print("-" * 80)
        
        result = calculate_customs_payments(scenario['spec'])
        
        print(f"Тип двигателя: {result.breakdown['engine_type_ru']}")
        print(f"Акциз: {result.excise_rub:,.0f} руб.")
        print(f"Пошлина: {result.duty_rub:,.0f} руб.")
        print(f"НДС: {result.vat_rub:,.0f} руб.")
        print(f"ИТОГО: {result.total_rub:,.0f} руб.")
    
    print("\n" + "=" * 90)
    print("📋 ИТОГОВАЯ ЛОГИКА ИНТЕРФЕЙСА:")
    print("=" * 90)
    print("1️⃣  Выбор типа топлива:")
    print("   • gasoline/diesel/electric → обычные типы, никаких доп. вопросов")
    print("   • diesel_electric/gasoline_electric → автоматически гибриды")
    print()
    print("2️⃣  Для гибридов только 2 вопроса:")
    print("   • Силовая установка последовательного типа? (да/нет)")
    print("   • Мощность ДВС больше максимальной 30-минутной мощности ЭД? (да/нет)")
    print()
    print("3️⃣  Что НЕ спрашивается:")
    print("   ❌ Гибридный или нет? (определяется автоматически)")
    print("   ❌ Мощность ДВС части (л.с.)")
    print("   ❌ Мощность электрической части (л.с.)")
    print()
    print("✅ РЕЗУЛЬТАТ: Максимально простой и понятный интерфейс!")
    print("=" * 90)

if __name__ == "__main__":
    demo_simplified_interface()