#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест упрощенной логики без вопросов про мощности ДВС и ЭД
"""

import sys
sys.path.append('.')

from customs_calculator_v5 import (
    VehicleSpec, VehicleType, ImporterType, EngineType, FuelType,
    calculate_customs_payments
)

def test_no_power_questions():
    """Тестирование упрощенной логики без отдельных мощностей ДВС и ЭД"""
    
    print("=" * 80)
    print("ТЕСТ УПРОЩЕННОЙ ЛОГИКИ БЕЗ ВОПРОСОВ ПРО МОЩНОСТИ ДВС И ЭД")
    print("=" * 80)
    
    # Тест 1: Гибрид последовательный, ЭД ≥ ДВС (считается как электромобиль)
    print("\n1. БЕНЗИН+ЭЛЕКТРО: Последовательный, ЭД ≥ ДВС")
    print("-" * 60)
    spec1 = VehicleSpec(
        vehicle_type=VehicleType.CAR,
        importer_type=ImporterType.PHYS_PERSONAL,
        cost_original=25000,
        currency='EUR',
        age_years=2,
        engine_volume_cc=2000,
        power_hp=200,  # Только общая мощность
        engine_type=EngineType.DVS,
        fuel_type=FuelType.GASOLINE_ELECTRIC,
        is_series_hybrid=True,
        dvs_power_greater_than_electric=False  # ЭД ≥ ДВС
        # НЕТ dvs_power_hp и electric_power_hp!
    )
    result1 = calculate_customs_payments(spec1)
    print(f"Тип двигателя: {result1.breakdown['engine_type_ru']}")
    print(f"Общая мощность: {spec1.power_hp} л.с.")
    print(f"Акциз: {result1.excise_rub:,.0f} руб. (считается как электромобиль)")
    print(f"Пошлина: {result1.duty_rub:,.0f} руб. (15% как электромобиль)")
    print(f"НДС: {result1.vat_rub:,.0f} руб. (20% как электромобиль)")
    
    # Тест 2: Гибрид последовательный, ДВС > ЭД (считается как ДВС)
    print("\n2. ДИЗЕЛЬ+ЭЛЕКТРО: Последовательный, ДВС > ЭД")
    print("-" * 60)
    spec2 = VehicleSpec(
        vehicle_type=VehicleType.CAR,
        importer_type=ImporterType.PHYS_PERSONAL,
        cost_original=25000,
        currency='EUR',
        age_years=2,
        engine_volume_cc=2000,
        power_hp=200,  # Только общая мощность
        engine_type=EngineType.DVS,
        fuel_type=FuelType.DIESEL_ELECTRIC,
        is_series_hybrid=True,
        dvs_power_greater_than_electric=True  # ДВС > ЭД
        # НЕТ dvs_power_hp и electric_power_hp!
    )
    result2 = calculate_customs_payments(spec2)
    print(f"Тип двигателя: {result2.breakdown['engine_type_ru']}")
    print(f"Общая мощность: {spec2.power_hp} л.с.")
    print(f"Акциз: {result2.excise_rub:,.0f} руб. (физлица освобождены от акциза на ДВС)")
    print(f"Пошлина: {result2.duty_rub:,.0f} руб. (по объему ДВС)")
    print(f"НДС: {result2.vat_rub:,.0f} руб. (физлица не платят НДС на ДВС)")
    
    # Тест 3: Гибрид параллельный (считается как ДВС)
    print("\n3. БЕНЗИН+ЭЛЕКТРО: Параллельный")
    print("-" * 60)
    spec3 = VehicleSpec(
        vehicle_type=VehicleType.CAR,
        importer_type=ImporterType.PHYS_PERSONAL,
        cost_original=25000,
        currency='EUR',
        age_years=2,
        engine_volume_cc=2000,
        power_hp=200,  # Только общая мощность
        engine_type=EngineType.DVS,
        fuel_type=FuelType.GASOLINE_ELECTRIC,
        is_series_hybrid=False,  # Параллельный
        dvs_power_greater_than_electric=True
        # НЕТ dvs_power_hp и electric_power_hp!
    )
    result3 = calculate_customs_payments(spec3)
    print(f"Тип двигателя: {result3.breakdown['engine_type_ru']}")
    print(f"Общая мощность: {spec3.power_hp} л.с.")
    print(f"Акциз: {result3.excise_rub:,.0f} руб. (физлица освобождены от акциза на ДВС)")
    print(f"Пошлина: {result3.duty_rub:,.0f} руб. (по объему ДВС)")
    print(f"НДС: {result3.vat_rub:,.0f} руб. (физлица не платят НДС на ДВС)")
    
    # Тест 4: Юридическое лицо
    print("\n4. ЮРЛИЦО: Дизель+Электро (последовательный, ЭД ≥ ДВС)")
    print("-" * 60)
    spec4 = VehicleSpec(
        vehicle_type=VehicleType.CAR,
        importer_type=ImporterType.JURIDICAL,
        cost_original=25000,
        currency='EUR',
        age_years=2,
        engine_volume_cc=2000,
        power_hp=200,  # Только общая мощность
        engine_type=EngineType.DVS,
        fuel_type=FuelType.DIESEL_ELECTRIC,
        is_series_hybrid=True,
        dvs_power_greater_than_electric=False  # ЭД ≥ ДВС
        # НЕТ dvs_power_hp и electric_power_hp!
    )
    result4 = calculate_customs_payments(spec4)
    print(f"Тип двигателя: {result4.breakdown['engine_type_ru']}")
    print(f"Общая мощность: {spec4.power_hp} л.с.")
    print(f"Акциз: {result4.excise_rub:,.0f} руб. (юрлица платят акциз)")
    print(f"Пошлина: {result4.duty_rub:,.0f} руб. (15% как электромобиль)")
    print(f"НДС: {result4.vat_rub:,.0f} руб. (юрлица всегда платят НДС)")
    
    print("\n" + "=" * 80)
    print("ВЫВОДЫ:")
    print("• Используется только общая мощность автомобиля")
    print("• НЕТ вопросов про мощность ДВС и электрической части")
    print("• Логика расчета основана на флагах is_series_hybrid и dvs_power_greater_than_electric")
    print("• Интерфейс максимально упрощен")
    print("=" * 80)

if __name__ == "__main__":
    test_no_power_questions()