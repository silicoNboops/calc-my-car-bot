from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from api.calculator.serializers import EstimateRequestSerializer
from api.calculator.services import CalculatorService, FixedCurrencyProvider, EstimateInput


@pytest.mark.django_db()
def test_serializer_age_key_forbidden_over5_for_jur() -> None:
    s = EstimateRequestSerializer(data={
        "price": 10000,
        "currency": "EUR",
        "engine_cc": 1600,
        "hp": 100,
        "engine_type": "Бензин",
        "age_key": "over_5",
        "is_jur": True,
    })
    assert not s.is_valid()
    assert "age_key" in s.errors


@pytest.mark.django_db()
def test_serializer_normalizes_phys_over7_to_over5() -> None:
    s = EstimateRequestSerializer(data={
        "price": 10000,
        "currency": "EUR",
        "engine_cc": 1600,
        "hp": 100,
        "engine_type": "Бензин",
        "age_key": "over_7",
        "is_jur": False,
    })
    assert s.is_valid(), s.errors
    assert s.validated_data["age_key"] == "over_5"
    # is_personal_use should default to not is_jur
    assert s.validated_data["is_personal_use"] is True


@pytest.mark.django_db()
@pytest.mark.parametrize("case", [
    {
        "title": "Физ <3 лет бензин 1999см³ 150лс 20k EUR",
        "payload": {
            "price": 20000.0,
            "currency": "EUR",
            "engine_cc": 1999,
            "hp": 150,
            "engine_type": "Бензин",
            "age_key": "under_3",
            "is_jur": False,
            "is_personal_use": True,
        },
    },
    {
        "title": "Физ 3-5 лет дизель 1600см³ 110лс 8k USD",
        "payload": {
            "price": 8000.0,
            "currency": "USD",
            "engine_cc": 1600,
            "hp": 110,
            "engine_type": "Дизель",
            "age_key": "3_to_5",
            "is_jur": False,
            "is_personal_use": True,
        },
    },
    {
        "title": "Юр бенз 3-5 лет 2200см³ 180лс 15k EUR",
        "payload": {
            "price": 15000.0,
            "currency": "EUR",
            "engine_cc": 2200,
            "hp": 180,
            "engine_type": "Бензин",
            "age_key": "3_to_5",
            "is_jur": True,
            "is_personal_use": False,
        },
    },
    {
        "title": ">=7 лет дизель юр 3000см³ 240лс 10k EUR",
        "payload": {
            "price": 10000.0,
            "currency": "EUR",
            "engine_cc": 3000,
            "hp": 240,
            "engine_type": "Дизель",
            "age_key": "over_7",
            "is_jur": True,
            "is_personal_use": False,
        },
    },
])
def test_estimate_endpoint_smoke(case: dict) -> None:
    client = APIClient()
    url = reverse("calculator:estimate")
    resp = client.post(url, data=case["payload"], format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    data = resp.json()
    # Basic shape
    for key in [
        "price_rub",
        "price_eur",
        "duty_eur",
        "duty_rub",
        "util_fee",
        "accise_rub",
        "vat_rub",
        "customs_fee",
        "subtotal_customs",
    ]:
        assert key in data
        assert isinstance(data[key], (int, float))
        assert data[key] >= 0


@pytest.mark.django_db()
def test_service_matches_endpoint_for_sample_case() -> None:
    # Select a sample case
    payload = {
        "price": 15000.0,
        "currency": "EUR",
        "engine_cc": 2200,
        "hp": 180,
        "engine_type": "Бензин",
        "age_key": "3_to_5",
        "is_jur": True,
        "is_personal_use": False,
    }

    # Call API
    client = APIClient()
    url = reverse("calculator:estimate")
    resp = client.post(url, data=payload, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    api_data = resp.json()

    # Call service directly
    svc = CalculatorService(FixedCurrencyProvider())
    calc = svc.build_calculator()
    res = calc.estimate(EstimateInput(**payload))

    # Compare main numbers with a small tolerance
    def almost(a: float, b: float, eps: float = 1e-6) -> bool:
        return abs(float(a) - float(b)) <= eps * max(1.0, abs(float(b)))

    assert almost(api_data["subtotal_customs"], res.subtotal_customs)
    assert almost(api_data["duty_rub"], res.duty_rub)
    assert almost(api_data["vat_rub"], res.vat_rub)
    assert almost(api_data["util_fee"], res.util_fee)
    assert almost(api_data["customs_fee"], res.customs_fee)
