from __future__ import annotations

import pytest

from api.calculator.models import Settings
from api.calculator.services import CalculatorService, CbrfCurrencyProvider, EstimateInput


@pytest.mark.django_db
def test_util_base_from_settings_affects_util_fee() -> None:
    # Входные данные: физлицо, under_3 — берётся util_fee kind=personal_new
    data = EstimateInput(
        price=10000.0,
        currency="EUR",
        engine_cc=1600,
        hp=120,
        engine_type="Бензин",
        age_key="under_3",
        is_jur=False,
        is_personal_use=True,
    )

    # 1) По умолчанию (нет Settings или default util_base=20000)
    svc = CalculatorService(CbrfCurrencyProvider())
    calc = svc.build_calculator()
    res1 = calc.estimate(data)

    # 2) Создаём явные Settings с util_base=30000 и пересобираем калькулятор
    Settings.objects.create(util_base=30000.0)

    svc2 = CalculatorService(CbrfCurrencyProvider())
    calc2 = svc2.build_calculator()
    res2 = calc2.estimate(data)

    # Проверяем, что утилизационный сбор масштабируется пропорционально util_base
    # Ожидаем отношение близкое к 1.5 (30000/20000)
    assert res1.util_fee > 0
    ratio = res2.util_fee / res1.util_fee
    assert ratio == pytest.approx(1.5, rel=1e-6)
