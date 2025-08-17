from __future__ import annotations

import pytest

from api.calculator.models import Settings
from api.calculator.services import CalculatorService, CbrfCurrencyProvider, EstimateInput


@pytest.mark.django_db
@pytest.mark.parametrize(
    "vehicle_type, age_key, is_jur, is_personal_use, expected_coeff",
    [
        ("quad", "under_3", False, True, 1.63),           # personal new
        ("quad", "over_5", True, None, 6.1),              # commercial old (jur)
        ("snowmobile", "under_3", False, True, 1.63),     # personal new
        ("motorcycle", "over_5", True, None, 6.1),        # commercial old (jur)
    ],
)
def test_util_fee_non_car_v2_coefficients(vehicle_type: str, age_key: str, is_jur: bool, is_personal_use: bool | None, expected_coeff: float) -> None:
    # Зафиксируем util_base, чтобы сверка шла 1:1 с v2 (172500 = 20000 * 8.625)
    Settings.objects.create(util_base=20000.0)

    svc = CalculatorService(CbrfCurrencyProvider())
    calc = svc.build_calculator()

    data = EstimateInput(
        price=10000.0,
        currency="EUR",
        engine_cc=800,
        hp=60,
        engine_type="Бензин",
        age_key=age_key,
        is_jur=is_jur,
        is_personal_use=is_personal_use,
        vehicle_type=vehicle_type,
    )

    res = calc.estimate(data)

    # Ожидаемая формула из реализации: util = util_base * 8.625 * coeff
    expected = 20000.0 * 8.625 * expected_coeff
    assert res.util_fee == pytest.approx(expected, rel=1e-9)
