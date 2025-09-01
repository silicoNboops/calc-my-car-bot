#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Демо-скрипт: имитация финального payload бота и прямой запуск v6 калькулятора.

Запуск:
    python -m calculator_v2.run_adapter_demo
или:
    python calculator_v2/run_adapter_demo.py
"""
from __future__ import annotations

from typing import Dict, Any

from .adapter import run_v6_with_bot_payload


def _print_result(tag: str, payload: Dict[str, Any]):
    print("\n" + "=" * 100)
    print(f"СЦЕНАРИЙ: {tag}")
    print("- payload:")
    for k, v in payload.items():
        print(f"  {k}: {v}")

    res = run_v6_with_bot_payload(payload)

    print("\nРЕЗУЛЬТАТ:")
    print(f"  Цена (RUB):         {res.cost_rub:,.2f}")
    print(f"  Пошлина (RUB):      {res.duty_rub:,.2f}")
    print(f"  Утилизац. сбор:     {res.util_fee_rub:,.2f}")
    print(f"  Акциз (RUB):        {res.excise_rub:,.2f}")
    print(f"  НДС (RUB):          {res.vat_rub:,.2f}")
    print(f"  Таможенный сбор:    {res.customs_fee_rub:,.2f}")
    print(f"  ИТОГО (RUB):        {res.total_rub:,.2f}")

    if res.breakdown:
        et = res.breakdown.get("engine_type_ru")
        if et:
            print(f"  Тип двигателя:      {et}")


def main():
    # 1) Физлицо, личное, легковой, бензин, до 3 лет
    payload1 = {
        "price": 25000.0,
        "currency": "EUR",
        "engine_cc": 2000,
        "hp": 0,  # в текущем визарде не спрашивается
        "engine_type": "Бензин",
        "age_key": "under_3",
        "is_jur": False,
        "is_personal_use": True,
        "vehicle_type": "car",
    }

    # 2) Юрлицо, легковой, дизель, 3–5 лет
    payload2 = {
        "price": 12000.0,
        "currency": "EUR",
        "engine_cc": 2200,
        "hp": 180,
        "engine_type": "Дизель",
        "age_key": "3_to_5",
        "is_jur": True,
        "is_personal_use": None,
        "vehicle_type": "car",
    }

    # 3) Физлицо, личное, электромобиль, до 3 лет
    payload3 = {
        "price": 30000.0,
        "currency": "EUR",
        "engine_cc": 0,
        "hp": 200,
        "engine_type": "Электро",
        "age_key": "under_3",
        "is_jur": False,
        "is_personal_use": True,
        "vehicle_type": "car",
    }

    # 4) Физлицо, перепродажа, гибрид (послед.), 5–7 лет
    payload4 = {
        "price": 17000.0,
        "currency": "EUR",
        "engine_cc": 1800,
        "hp": 150,
        "engine_type": "Гибрид(послед)",
        "age_key": "5_to_7",
        "is_jur": False,
        "is_personal_use": False,
        "vehicle_type": "car",
    }

    for i, (tag, p) in enumerate([
        ("ФЛ личное бензин <3", payload1),
        ("ЮЛ дизель 3–5", payload2),
        ("ФЛ личное электро <3", payload3),
        ("ФЛ перепродажа гибрид(послед) 5–7", payload4),
    ], 1):
        _print_result(f"{i}. {tag}", p)


if __name__ == "__main__":
    main()
