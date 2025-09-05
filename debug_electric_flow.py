#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Отладка потока выбора электромобиля
"""

# Симуляция выбора электромобиля
def debug_electric_flow():
    print("🔍 ОТЛАДКА ПОТОКА ЭЛЕКТРОМОБИЛЯ")
    print("=" * 50)
    
    # Импортируем choices
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    from api.calculator.choices import EngineType as EngineTypeChoices, VehicleType as VehicleTypeChoices
    
    print("1️⃣ Доступные типы двигателей:")
    for kind, title in EngineTypeChoices.choices:
        print(f"   {kind} -> {title}")
    
    print("\n2️⃣ Доступные типы ТС:")
    for kind, title in VehicleTypeChoices.choices:
        print(f"   {kind} -> {title}")
    
    print("\n3️⃣ Проверка условий для запроса мощности:")
    
    # Симуляция данных
    test_cases = [
        ("car", "Электро"),
        ("motorcycle", "Электро"),
        ("quad", "Электро"),
        ("snowmobile", "Электро"),
    ]
    
    for vehicle_type, engine_type in test_cases:
        print(f"\n   Тип ТС: {vehicle_type}, Двигатель: {engine_type}")
        
        # Проверяем условие из строки 354
        if engine_type == EngineTypeChoices.ELECTRO:
            print("   ✅ Это электромобиль")
            
            # Проверяем условие из строки 354
            if vehicle_type in {VehicleTypeChoices.CAR, VehicleTypeChoices.MOTORCYCLE}:
                print("   ✅ Car/Motorcycle - должен запросить мощность (строки 354-362)")
            else:
                print("   ✅ Quad/Snowmobile - тоже должен запросить мощность (строки 365-372)")
        else:
            print("   ❌ Не электромобиль")
    
    print("\n4️⃣ Проверка логики use_kw_30min:")
    engine_types_to_test = [
        EngineTypeChoices.ELECTRO,
        EngineTypeChoices.HYBRID_SERIES,
        EngineTypeChoices.HYBRID_PARALLEL,
        EngineTypeChoices.BENZIN,
        EngineTypeChoices.DIESEL,
    ]
    
    for et in engine_types_to_test:
        use_kw_30min = et in {EngineTypeChoices.ELECTRO, EngineTypeChoices.HYBRID_SERIES}
        print(f"   {et}: use_kw_30min = {use_kw_30min}")

if __name__ == "__main__":
    debug_electric_flow()