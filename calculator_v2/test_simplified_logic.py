#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест упрощенной логики выбора типа двигателя
"""

import sys
sys.path.append('.')

from customs_calculator_v6 import (
    VehicleSpec, VehicleType, ImporterType, EngineType, FuelType,
    calculate_customs_payments
)

def test_simplified_logic():
    """Тестирование упрощенной логики выбора типа двигателя"""
    
    print("=" * 80)
    print("ТЕСТ УПРОЩЕННОЙ ЛОГИКИ ВЫБОРА ТИПА ДВИГАТЕЛЯ")
    print("=" * 80)
    
    # Тест 1: Обычный бензиновый автомобиль (НЕ гибрид)
    print("\n1. БЕНЗИНОВЫЙ АВТОМОБИЛЬ (обычный ДВС)")
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
        fuel_type=FuelType.GASOLINE
    )
    result1 = calculate_customs_payments(spec1)
    print(f"Тип двигателя: {result1.breakdown['engine_type_ru']}")
    print(f"Акциз: {result1.excise_rub:,.0f} руб. (физлица освобождены от акциза на ДВС)")
    print(f"НДС: {result1.vat_rub:,.0f} руб. (физлица не платят НДС на ДВС)")
    
    # Тест 2: Обычный дизельный автомобиль (НЕ гибрид)
    print("\n2. ДИЗЕЛЬНЫЙ АВТОМОБИЛЬ (обычный ДВС)")
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
        fuel_type=FuelType.DIESEL
    )
    result2 = calculate_customs_payments(spec2)
    print(f"Тип двигателя: {result2.breakdown['engine_type_ru']}")
    print(f"Акциз: {result2.excise_rub:,.0f} руб. (физлица освобождены от акциза на ДВС)")
    print(f"НДС: {result2.vat_rub:,.0f} руб. (физлица не платят НДС на ДВС)")
    
    # Тест 3: Электромобиль
    print("\n3. ЭЛЕКТРОМОБИЛЬ")
    print("-" * 60)
    spec3 = VehicleSpec(
        vehicle_type=VehicleType.CAR,
        importer_type=ImporterType.PHYS_PERSONAL,
        cost_original=25000,
        currency='EUR',
        age_years=2,
        engine_volume_cc=0,
        power_hp=200,
        engine_type=EngineType.ELECTRIC,
        fuel_type=FuelType.ELECTRIC
    )
    result3 = calculate_customs_payments(spec3)
    print(f"Тип двигателя: {result3.breakdown['engine_type_ru']}")
    print(f"Акциз: {result3.excise_rub:,.0f} руб. (электромобили облагаются акцизом)")
    print(f"НДС: {result3.vat_rub:,.0f} руб. (электромобили облагаются НДС)")
    
    # Тест 4: Гибрид дизель+электро (автоматически гибрид)
    print("\n4. ДИЗЕЛЬ+ЭЛЕКТРО (автоматически гибрид)")
    print("-" * 60)
    spec4 = VehicleSpec(
        vehicle_type=VehicleType.CAR,
        importer_type=ImporterType.PHYS_PERSONAL,
        cost_original=25000,
        currency='EUR',
        age_years=2,
        engine_volume_cc=2000,
        power_hp=200,
        engine_type=EngineType.DVS,
        dvs_power_hp=90,
        electric_power_hp=130,
        fuel_type=FuelType.DIESEL_ELECTRIC,
        is_series_hybrid=True,
        dvs_power_greater_than_electric=False  # ЭД ≥ ДВС
    )
    result4 = calculate_customs_payments(spec4)
    print(f"Тип двигателя: {result4.breakdown['engine_type_ru']}")
    print(f"Акциз: {result4.excise_rub:,.0f} руб. (считается как электромобиль)")
    print(f"НДС: {result4.vat_rub:,.0f} руб. (считается как электромобиль)")
    
    # Тест 5: Гибрид бензин+электро (автоматически гибрид)
    print("\n5. БЕНЗИН+ЭЛЕКТРО (автоматически гибрид)")
    print("-" * 60)
    spec5 = VehicleSpec(
        vehicle_type=VehicleType.CAR,
        importer_type=ImporterType.PHYS_PERSONAL,
        cost_original=25000,
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
    result5 = calculate_customs_payments(spec5)
    print(f"Тип двигателя: {result5.breakdown['engine_type_ru']}")
    print(f"Акциз: {result5.excise_rub:,.0f} руб. (считается как ДВС)")
    print(f"НДС: {result5.vat_rub:,.0f} руб. (считается как ДВС)")
    
    print("\n" + "=" * 80)
    print("ВЫВОДЫ УПРОЩЕННОЙ ЛОГИКИ:")
    print("• gasoline → обычный ДВС (НЕ гибрид)")
    print("• diesel → обычный ДВС (НЕ гибрид)")
    print("• electric → электромобиль")
    print("• diesel_electric → автоматически гибрид")
    print("• gasoline_electric → автоматически гибрид")
    print("• Никаких дополнительных вопросов про 'гибридный или нет'")
    print("=" * 80)

if __name__ == "__main__":
    test_simplified_logic()